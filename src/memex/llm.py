"""LLM integration for memory evolution via OpenRouter.

This module provides async functions for LLM-driven memory evolution,
where neighbors of new entries are analyzed and their keywords/context
updated based on the relationship.

Uses OpenRouter as a model-agnostic LLM gateway with OpenAI SDK compatibility.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

log = logging.getLogger(__name__)

# OpenRouter API endpoint (OpenAI SDK compatible)
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass
class EvolutionSuggestion:
    """Suggested updates for a neighbor entry based on a new connection."""

    neighbor_path: str
    """Path to the neighbor entry being evolved."""

    add_keywords: list[str]
    """Keywords to add to the neighbor (0-3 typically)."""

    relationship: str
    """One-sentence description of the relationship, or empty string."""


class LLMConfigurationError(Exception):
    """Raised when LLM is not properly configured."""

    pass


def _get_openai_client():
    """Get an AsyncOpenAI client configured for OpenRouter.

    Raises:
        LLMConfigurationError: If OPENROUTER_API_KEY is not set.

    Returns:
        AsyncOpenAI client configured for OpenRouter.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise LLMConfigurationError(
            "OPENROUTER_API_KEY environment variable is required for memory evolution. "
            "Get an API key at https://openrouter.ai/keys"
        )

    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise LLMConfigurationError(
            "openai package is required for memory evolution. "
            "Install with: uv add openai"
        )

    return AsyncOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
    )


async def evolve_single_neighbor(
    new_entry_title: str,
    new_entry_content: str,
    new_entry_keywords: list[str],
    neighbor_path: str,
    neighbor_title: str,
    neighbor_content: str,
    neighbor_keywords: list[str],
    link_score: float,
    model: str,
    max_keywords: int = 3,
) -> EvolutionSuggestion:
    """Analyze relationship between new entry and neighbor, suggest updates.

    Args:
        new_entry_title: Title of the newly added entry.
        new_entry_content: Content of the new entry (may be truncated).
        new_entry_keywords: Keywords of the new entry.
        neighbor_path: Path to the neighbor entry.
        neighbor_title: Title of the neighbor entry.
        neighbor_content: Content of the neighbor (may be truncated).
        neighbor_keywords: Current keywords of the neighbor.
        link_score: Similarity score between entries (0.0-1.0).
        model: OpenRouter model ID to use.
        max_keywords: Maximum keywords to suggest adding.

    Returns:
        EvolutionSuggestion with keywords to add and relationship description.

    Raises:
        LLMConfigurationError: If API key not configured.
        Exception: On API errors.
    """
    client = _get_openai_client()

    score_str = f"{link_score:.2f}"
    new_kw_str = ", ".join(new_entry_keywords) if new_entry_keywords else "none"
    neighbor_kw_str = ", ".join(neighbor_keywords) if neighbor_keywords else "none"

    prompt = f"""A new KB entry was linked to an existing entry (similarity: {score_str}).

NEW ENTRY:
Title: {new_entry_title}
Keywords: {new_kw_str}
Content (first 500 chars): {new_entry_content[:500]}

EXISTING ENTRY (to evolve):
Title: {neighbor_title}
Keywords: {neighbor_kw_str}
Content (first 500 chars): {neighbor_content[:500]}

Based on this connection, suggest updates for the EXISTING entry:
1. 0-{max_keywords} keywords to ADD (only if genuinely relevant, avoid duplicates)
2. One sentence describing this relationship (or empty string if weak)

Respond with JSON only:
{{"add_keywords": ["kw1", "kw2"], "relationship": "sentence or empty string"}}"""

    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,  # Low temperature for consistent, focused suggestions
    )

    try:
        result = json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, IndexError, AttributeError) as e:
        log.warning("Failed to parse LLM response for evolution: %s", e)
        return EvolutionSuggestion(
            neighbor_path=neighbor_path,
            add_keywords=[],
            relationship="",
        )

    # Validate and sanitize keywords
    add_keywords = result.get("add_keywords", [])
    if not isinstance(add_keywords, list):
        add_keywords = []
    add_keywords = [str(kw).strip().lower() for kw in add_keywords if kw]
    add_keywords = add_keywords[:max_keywords]

    # Filter out keywords that already exist
    existing_lower = {kw.lower() for kw in neighbor_keywords}
    add_keywords = [kw for kw in add_keywords if kw not in existing_lower]

    relationship = result.get("relationship", "")
    if not isinstance(relationship, str):
        relationship = ""
    relationship = relationship.strip()

    return EvolutionSuggestion(
        neighbor_path=neighbor_path,
        add_keywords=add_keywords,
        relationship=relationship,
    )


@dataclass
class NeighborInfo:
    """Information about a neighbor entry for batched evolution."""

    path: str
    title: str
    content: str
    keywords: list[str]
    score: float


async def evolve_neighbors_batched(
    new_entry_title: str,
    new_entry_content: str,
    new_entry_keywords: list[str],
    neighbors: list[NeighborInfo],
    model: str,
    max_keywords: int = 3,
) -> list[EvolutionSuggestion]:
    """Analyze relationships with multiple neighbors in a single LLM call.

    More efficient than individual calls when linking to multiple neighbors.

    Args:
        new_entry_title: Title of the newly added entry.
        new_entry_content: Content of the new entry.
        new_entry_keywords: Keywords of the new entry.
        neighbors: List of neighbor entries to analyze.
        model: OpenRouter model ID to use.
        max_keywords: Maximum keywords per neighbor.

    Returns:
        List of EvolutionSuggestions, one per neighbor.
    """
    if not neighbors:
        return []

    # For single neighbor, use the simpler prompt
    if len(neighbors) == 1:
        n = neighbors[0]
        return [
            await evolve_single_neighbor(
                new_entry_title=new_entry_title,
                new_entry_content=new_entry_content,
                new_entry_keywords=new_entry_keywords,
                neighbor_path=n.path,
                neighbor_title=n.title,
                neighbor_content=n.content,
                neighbor_keywords=n.keywords,
                link_score=n.score,
                model=model,
                max_keywords=max_keywords,
            )
        ]

    client = _get_openai_client()

    # Build neighbor descriptions
    neighbor_sections = []
    for i, n in enumerate(neighbors):
        section = f"""NEIGHBOR {i + 1} (path: {n.path}, similarity: {n.score:.2f}):
Title: {n.title}
Keywords: {', '.join(n.keywords) if n.keywords else 'none'}
Content (first 300 chars): {n.content[:300]}"""
        neighbor_sections.append(section)

    new_kw_str = ", ".join(new_entry_keywords) if new_entry_keywords else "none"

    prompt = f"""A new KB entry was linked to multiple existing entries.

NEW ENTRY:
Title: {new_entry_title}
Keywords: {new_kw_str}
Content (first 400 chars): {new_entry_content[:400]}

{chr(10).join(neighbor_sections)}

For EACH neighbor, suggest updates based on the connection to the new entry:
1. 0-{max_keywords} keywords to ADD (only if genuinely relevant, avoid duplicates)
2. One sentence describing this relationship (or empty string if weak)

Respond with JSON array, one object per neighbor in order:
[{{"path": "neighbor_path", "add_keywords": ["kw1"], "relationship": "sentence"}}]"""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )

        # Parse response - might be wrapped in an object
        raw = response.choices[0].message.content
        parsed = json.loads(raw)

        # Handle both array and object with "neighbors" key
        if isinstance(parsed, list):
            results = parsed
        elif isinstance(parsed, dict):
            results = parsed.get("neighbors", parsed.get("results", []))
        else:
            results = []

    except (json.JSONDecodeError, IndexError, AttributeError) as e:
        log.warning("Failed to parse batched LLM response: %s", e)
        results = []
    except Exception as e:
        log.warning("LLM API error during batched evolution: %s", e)
        results = []

    # Build suggestions, filling in defaults for missing/invalid entries
    suggestions = []
    for i, n in enumerate(neighbors):
        if i < len(results) and isinstance(results[i], dict):
            r = results[i]
            add_keywords = r.get("add_keywords", [])
            if not isinstance(add_keywords, list):
                add_keywords = []
            add_keywords = [str(kw).strip().lower() for kw in add_keywords if kw]
            add_keywords = add_keywords[:max_keywords]

            # Filter out existing keywords
            existing_lower = {kw.lower() for kw in n.keywords}
            add_keywords = [kw for kw in add_keywords if kw not in existing_lower]

            relationship = r.get("relationship", "")
            if not isinstance(relationship, str):
                relationship = ""
        else:
            add_keywords = []
            relationship = ""

        suggestions.append(
            EvolutionSuggestion(
                neighbor_path=n.path,
                add_keywords=add_keywords,
                relationship=relationship.strip(),
            )
        )

    return suggestions
