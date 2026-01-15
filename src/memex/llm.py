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

    new_keywords: list[str]
    """Complete new keyword list for the neighbor (replaces existing)."""

    relationship: str
    """One-sentence description of the relationship, or empty string."""

    new_context: str = ""
    """Updated context/description for the neighbor (one sentence describing semantic role)."""


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

    Returns:
        EvolutionSuggestion with new keywords (replaces existing) and relationship.

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
Current keywords: {neighbor_kw_str}
Content (first 500 chars): {neighbor_content[:500]}

Based on this new connection, suggest the COMPLETE new keyword list for the EXISTING entry.
The new list should:
- Keep relevant existing keywords
- Add new keywords based on the connection (if genuinely relevant)
- Remove keywords that are no longer appropriate
- Typically contain 3-7 keywords total

Also provide:
1. One sentence describing this relationship (or empty string if weak)
2. Updated context: a single sentence describing the EXISTING entry's semantic role in the KB

Respond with JSON only:
{{"new_keywords": ["kw1", "kw2", "kw3"], "relationship": "sentence or empty",
"new_context": "one sentence describing what this entry is about"}}"""

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
            new_keywords=neighbor_keywords,  # Preserve existing on error
            relationship="",
            new_context="",
        )

    # Validate and sanitize keywords
    new_keywords = result.get("new_keywords", [])
    if not isinstance(new_keywords, list):
        new_keywords = neighbor_keywords  # Preserve existing on invalid response
    else:
        new_keywords = [str(kw).strip().lower() for kw in new_keywords if kw]
        if not new_keywords:
            new_keywords = neighbor_keywords  # Preserve existing if empty

    relationship = result.get("relationship", "")
    if not isinstance(relationship, str):
        relationship = ""
    relationship = relationship.strip()

    new_context = result.get("new_context", "")
    if not isinstance(new_context, str):
        new_context = ""
    new_context = new_context.strip()

    return EvolutionSuggestion(
        neighbor_path=neighbor_path,
        new_keywords=new_keywords,
        relationship=relationship,
        new_context=new_context,
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
) -> list[EvolutionSuggestion]:
    """Analyze relationships with multiple neighbors in a single LLM call.

    More efficient than individual calls when linking to multiple neighbors.

    Args:
        new_entry_title: Title of the newly added entry.
        new_entry_content: Content of the new entry.
        new_entry_keywords: Keywords of the new entry.
        neighbors: List of neighbor entries to analyze.
        model: OpenRouter model ID to use.

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
            )
        ]

    client = _get_openai_client()

    # Build neighbor descriptions
    neighbor_sections = []
    for i, n in enumerate(neighbors):
        section = f"""NEIGHBOR {i + 1} (path: {n.path}, similarity: {n.score:.2f}):
Title: {n.title}
Current keywords: {', '.join(n.keywords) if n.keywords else 'none'}
Content (first 300 chars): {n.content[:300]}"""
        neighbor_sections.append(section)

    new_kw_str = ", ".join(new_entry_keywords) if new_entry_keywords else "none"

    prompt = f"""A new KB entry was linked to multiple existing entries.

NEW ENTRY:
Title: {new_entry_title}
Keywords: {new_kw_str}
Content (first 400 chars): {new_entry_content[:400]}

{chr(10).join(neighbor_sections)}

For EACH neighbor, suggest the COMPLETE new keyword list based on the connection to the new entry.
Each new list should:
- Keep relevant existing keywords
- Add new keywords based on the connection (if genuinely relevant)
- Remove keywords that are no longer appropriate
- Typically contain 3-7 keywords total

Also provide:
1. One sentence describing the relationship (or empty string if weak)
2. Updated context: a single sentence describing that neighbor's semantic role in the KB

Respond with JSON array, one object per neighbor in order:
[{{"path": "neighbor_path", "new_keywords": ["kw1", "kw2"], "relationship": "sentence",
"new_context": "one sentence describing what this entry is about"}}]"""

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
            new_keywords = r.get("new_keywords", [])
            if not isinstance(new_keywords, list):
                new_keywords = n.keywords  # Preserve existing on invalid
            else:
                new_keywords = [str(kw).strip().lower() for kw in new_keywords if kw]
                if not new_keywords:
                    new_keywords = n.keywords  # Preserve existing if empty

            relationship = r.get("relationship", "")
            if not isinstance(relationship, str):
                relationship = ""

            new_context = r.get("new_context", "")
            if not isinstance(new_context, str):
                new_context = ""
        else:
            new_keywords = n.keywords  # Preserve existing on missing
            relationship = ""
            new_context = ""

        suggestions.append(
            EvolutionSuggestion(
                neighbor_path=n.path,
                new_keywords=new_keywords,
                relationship=relationship.strip(),
                new_context=new_context.strip(),
            )
        )

    return suggestions


def _extract_first_json_object(text: str) -> dict:
    """Extract the first valid JSON object from text.

    Some models return extra content after the JSON object even with
    response_format=json_object. This function finds and parses just
    the first complete JSON object.

    Args:
        text: Raw text that may contain JSON plus extra content.

    Returns:
        Parsed dict from the first JSON object.

    Raises:
        json.JSONDecodeError: If no valid JSON object found.
    """
    # Try parsing the whole thing first (common case)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the first { and try to match the closing }
    start = text.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", text, 0)

    # Count braces to find matching close
    depth = 0
    in_string = False
    escape_next = False

    for i, char in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                # Found complete object
                return json.loads(text[start : i + 1])

    # No complete object found
    raise json.JSONDecodeError("Incomplete JSON object", text, len(text))


@dataclass
class KeywordExtractionResult:
    """Result of LLM keyword extraction for an entry."""

    keywords: list[str]
    """Extracted keywords (3-6 typically)."""

    success: bool
    """Whether extraction succeeded."""

    error: str | None = None
    """Error message if extraction failed."""


async def extract_keywords_llm(
    content: str,
    title: str,
    model: str,
    min_keywords: int = 3,
    max_keywords: int = 6,
) -> KeywordExtractionResult:
    """Extract keywords from content using LLM.

    Args:
        content: The entry content to analyze.
        title: Entry title for context.
        model: OpenRouter model ID to use.
        min_keywords: Minimum keywords to extract.
        max_keywords: Maximum keywords to extract.

    Returns:
        KeywordExtractionResult with extracted keywords or error info.

    Raises:
        LLMConfigurationError: If API key not configured.
    """
    client = _get_openai_client()

    # Truncate content to avoid excessive tokens
    content_preview = content[:2000] if len(content) > 2000 else content

    prompt = f"""Extract {min_keywords}-{max_keywords} keywords from this content.
Keywords should be:
- Domain-specific concepts (not generic words)
- Key entities, technologies, or patterns mentioned
- Related concepts that aid discoverability

Title: {title}
Content:
{content_preview}

Return JSON: {{"keywords": ["keyword1", "keyword2", ...]}}"""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=256,  # Keywords only need minimal tokens
        )

        content = response.choices[0].message.content or ""
        # Some models return extra data after JSON - extract first valid object
        result = _extract_first_json_object(content)
        keywords = result.get("keywords", [])

        # Validate and sanitize
        if not isinstance(keywords, list):
            keywords = []
        keywords = [str(kw).strip().lower() for kw in keywords if kw]
        keywords = [kw for kw in keywords if kw]  # Remove empty strings
        keywords = keywords[:max_keywords]

        if not keywords:
            return KeywordExtractionResult(
                keywords=[],
                success=False,
                error="LLM returned no keywords",
            )

        return KeywordExtractionResult(
            keywords=keywords,
            success=True,
        )

    except json.JSONDecodeError as e:
        log.warning("Failed to parse LLM keyword response: %s", e)
        return KeywordExtractionResult(
            keywords=[],
            success=False,
            error=f"JSON parse error: {e}",
        )
    except Exception as e:
        log.warning("LLM API error during keyword extraction: %s", e)
        return KeywordExtractionResult(
            keywords=[],
            success=False,
            error=str(e),
        )
