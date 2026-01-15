"""Tests for memory evolution (A-Mem style keyword/context evolution)."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from memex import core
from memex.config import MemoryEvolutionConfig, get_memory_evolution_config
from memex.llm import (
    EvolutionSuggestion,
    LLMConfigurationError,
    NeighborInfo,
    evolve_neighbors_batched,
    evolve_single_neighbor,
)


class TestMemoryEvolutionConfig:
    """Tests for memory evolution configuration loading."""

    def test_default_config_disabled(self, tmp_path, monkeypatch):
        """Default config has evolution disabled."""
        # No .kbconfig file
        monkeypatch.chdir(tmp_path)
        config = get_memory_evolution_config()
        assert config.enabled is False
        assert config.model == "anthropic/claude-3-5-haiku"
        assert config.min_score == 0.7

    def test_loads_from_kbconfig(self, tmp_path, monkeypatch):
        """Config loads from .kbconfig memory_evolution section."""
        kbconfig = tmp_path / ".kbconfig"
        kb_path = tmp_path / "kb"
        kb_path.mkdir()
        kbconfig.write_text(
            """
kb_path: kb
memory_evolution:
  enabled: true
  model: openai/gpt-4o-mini
  min_score: 0.8
"""
        )
        monkeypatch.chdir(tmp_path)

        config = get_memory_evolution_config()
        assert config.enabled is True
        assert config.model == "openai/gpt-4o-mini"
        assert config.min_score == 0.8

    def test_partial_config_uses_defaults(self, tmp_path, monkeypatch):
        """Partial config fills in defaults."""
        kbconfig = tmp_path / ".kbconfig"
        kb_path = tmp_path / "kb"
        kb_path.mkdir()
        kbconfig.write_text(
            """
kb_path: kb
memory_evolution:
  enabled: true
"""
        )
        monkeypatch.chdir(tmp_path)

        config = get_memory_evolution_config()
        assert config.enabled is True
        assert config.model == "anthropic/claude-3-5-haiku"  # default
        assert config.min_score == 0.7  # default


class TestLLMEvolution:
    """Tests for LLM-based evolution functions."""

    def test_missing_api_key_raises_error(self, monkeypatch):
        """Missing OPENROUTER_API_KEY raises LLMConfigurationError."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        from memex.llm import _get_openai_client

        with pytest.raises(LLMConfigurationError, match="OPENROUTER_API_KEY"):
            _get_openai_client()

    @pytest.mark.asyncio
    async def test_evolve_single_neighbor_parses_response(self, monkeypatch):
        """evolve_single_neighbor correctly parses LLM JSON response."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        # Mock the OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {"new_keywords": ["python", "testing"], "relationship": "Related to testing concepts"}
                    )
                )
            )
        ]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("memex.llm._get_openai_client", return_value=mock_client):
            result = await evolve_single_neighbor(
                new_entry_title="Test Entry",
                new_entry_content="Content about testing",
                new_entry_keywords=["testing"],
                neighbor_path="guides/python.md",
                neighbor_title="Python Guide",
                neighbor_content="Guide about Python programming",
                neighbor_keywords=["python"],
                link_score=0.75,
                model="anthropic/claude-3-5-haiku",
            )

        assert result.neighbor_path == "guides/python.md"
        assert result.new_keywords == ["python", "testing"]  # Complete replacement list
        assert result.relationship == "Related to testing concepts"
        assert result.new_context == ""  # Not provided in response

    @pytest.mark.asyncio
    async def test_evolve_single_neighbor_parses_new_context(self, monkeypatch):
        """evolve_single_neighbor correctly parses new_context from LLM response."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "new_keywords": ["python", "testing"],
                        "relationship": "Related to testing",
                        "new_context": "A guide covering Python testing fundamentals."
                    })
                )
            )
        ]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("memex.llm._get_openai_client", return_value=mock_client):
            result = await evolve_single_neighbor(
                new_entry_title="Test Entry",
                new_entry_content="Content about testing",
                new_entry_keywords=["testing"],
                neighbor_path="guides/python.md",
                neighbor_title="Python Guide",
                neighbor_content="Guide about Python programming",
                neighbor_keywords=["python"],
                link_score=0.75,
                model="test-model",
            )

        assert result.new_keywords == ["python", "testing"]
        assert result.new_context == "A guide covering Python testing fundamentals."

    @pytest.mark.asyncio
    async def test_evolve_single_neighbor_handles_invalid_json(self, monkeypatch):
        """evolve_single_neighbor handles invalid JSON gracefully."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="not valid json"))]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("memex.llm._get_openai_client", return_value=mock_client):
            result = await evolve_single_neighbor(
                new_entry_title="Test",
                new_entry_content="Content",
                new_entry_keywords=[],
                neighbor_path="test.md",
                neighbor_title="Test",
                neighbor_content="Test content",
                neighbor_keywords=["existing"],
                link_score=0.8,
                model="test-model",
            )

        assert result.new_keywords == ["existing"]  # Preserves existing on error
        assert result.relationship == ""

    @pytest.mark.asyncio
    async def test_evolve_neighbors_batched_single_neighbor(self, monkeypatch):
        """evolve_neighbors_batched uses single-neighbor path for 1 neighbor."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({"new_keywords": ["new", "existing"], "relationship": "test"})))
        ]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("memex.llm._get_openai_client", return_value=mock_client):
            neighbors = [NeighborInfo(path="test.md", title="Test", content="Content", keywords=["existing"], score=0.8)]

            results = await evolve_neighbors_batched(
                new_entry_title="New Entry",
                new_entry_content="New content",
                new_entry_keywords=["new"],
                neighbors=neighbors,
                model="test-model",
            )

        assert len(results) == 1
        assert results[0].new_keywords == ["new", "existing"]

    @pytest.mark.asyncio
    async def test_evolve_neighbors_batched_multiple(self, monkeypatch):
        """evolve_neighbors_batched handles multiple neighbors."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        # Response is a JSON object with an array (common LLM format)
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        [
                            {"path": "a.md", "new_keywords": ["kw1", "existing_a"], "relationship": "rel1"},
                            {"path": "b.md", "new_keywords": ["kw2"], "relationship": "rel2"},
                        ]
                    )
                )
            )
        ]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("memex.llm._get_openai_client", return_value=mock_client):
            neighbors = [
                NeighborInfo(path="a.md", title="A", content="Content A", keywords=["existing_a"], score=0.8),
                NeighborInfo(path="b.md", title="B", content="Content B", keywords=["old_b"], score=0.75),
            ]

            results = await evolve_neighbors_batched(
                new_entry_title="New",
                new_entry_content="Content",
                new_entry_keywords=[],
                neighbors=neighbors,
                model="test-model",
            )

        assert len(results) == 2
        assert results[0].new_keywords == ["kw1", "existing_a"]
        assert results[1].new_keywords == ["kw2"]

    @pytest.mark.asyncio
    async def test_evolve_neighbors_batched_parses_new_context(self, monkeypatch):
        """evolve_neighbors_batched correctly parses new_context for each neighbor."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps([
                        {
                            "path": "a.md",
                            "new_keywords": ["kw1"],
                            "relationship": "rel1",
                            "new_context": "Entry A describes core concepts.",
                        },
                        {
                            "path": "b.md",
                            "new_keywords": ["kw2"],
                            "relationship": "rel2",
                            "new_context": "Entry B covers advanced topics.",
                        },
                    ])
                )
            )
        ]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("memex.llm._get_openai_client", return_value=mock_client):
            neighbors = [
                NeighborInfo(path="a.md", title="A", content="Content A", keywords=["existing_a"], score=0.8),
                NeighborInfo(path="b.md", title="B", content="Content B", keywords=["old_b"], score=0.75),
            ]

            results = await evolve_neighbors_batched(
                new_entry_title="New",
                new_entry_content="Content",
                new_entry_keywords=[],
                neighbors=neighbors,
                model="test-model",
            )

        assert len(results) == 2
        assert results[0].new_context == "Entry A describes core concepts."
        assert results[1].new_context == "Entry B covers advanced topics."

    @pytest.mark.asyncio
    async def test_evolve_replaces_keywords_not_appends(self, monkeypatch):
        """LLM response replaces keywords entirely, doesn't append."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        # LLM returns complete new list (kept "existing", added "new", dropped "old")
                        {"new_keywords": ["existing", "new"], "relationship": ""}
                    )
                )
            )
        ]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("memex.llm._get_openai_client", return_value=mock_client):
            result = await evolve_single_neighbor(
                new_entry_title="Test",
                new_entry_content="Content",
                new_entry_keywords=[],
                neighbor_path="test.md",
                neighbor_title="Test",
                neighbor_content="Content",
                neighbor_keywords=["existing", "old"],  # Had "existing" and "old"
                link_score=0.8,
                model="test-model",
            )

        # Result is the complete replacement list from LLM
        assert result.new_keywords == ["existing", "new"]


class TestQueueEvolution:
    """Integration tests for queue-based evolution in core.py."""

    @pytest.fixture
    def tmp_kb(self, tmp_path, monkeypatch):
        """Create a temporary KB directory."""
        kb_path = tmp_path / "kb"
        kb_path.mkdir()
        (kb_path / ".kbconfig").write_text("kb_path: .")
        (kb_path / ".indices").mkdir()
        (kb_path / "test").mkdir()

        # Set up environment
        monkeypatch.setenv("MEMEX_SKIP_PROJECT_KB", "")
        monkeypatch.chdir(kb_path)

        return kb_path

    def test_queue_evolution_skipped_when_disabled(self, tmp_kb, monkeypatch):
        """Queueing is skipped when disabled in config."""
        monkeypatch.setattr(
            "memex.core.get_memory_evolution_config",
            lambda: MemoryEvolutionConfig(enabled=False),
        )

        count = core._queue_evolution(
            new_entry_path="test/new.md",
            neighbors_to_evolve=[("test/neighbor.md", 0.8)],
            kb_root=tmp_kb,
        )
        assert count == 0

    def test_queue_evolution_filters_by_min_score(self, tmp_kb, monkeypatch):
        """Only neighbors above min_score are queued."""
        monkeypatch.setattr(
            "memex.core.get_memory_evolution_config",
            lambda: MemoryEvolutionConfig(enabled=True, min_score=0.8),
        )

        # All neighbors below threshold
        count = core._queue_evolution(
            new_entry_path="test/new.md",
            neighbors_to_evolve=[("test/a.md", 0.7), ("test/b.md", 0.6)],
            kb_root=tmp_kb,
        )
        assert count == 0

    def test_queue_evolution_queues_valid_neighbors(self, tmp_kb, monkeypatch):
        """Neighbors above min_score are queued."""
        monkeypatch.setattr(
            "memex.core.get_memory_evolution_config",
            lambda: MemoryEvolutionConfig(enabled=True, min_score=0.7),
        )

        count = core._queue_evolution(
            new_entry_path="test/new.md",
            neighbors_to_evolve=[("test/a.md", 0.8), ("test/b.md", 0.6)],
            kb_root=tmp_kb,
        )
        # Only test/a.md should be queued (0.8 >= 0.7)
        assert count == 1

        # Verify queue contents
        from memex.evolution_queue import read_queue
        items = read_queue(tmp_kb)
        assert len(items) == 1
        assert items[0].neighbor == "test/a.md"


class TestProcessEvolutionItems:
    """Integration tests for process_evolution_items in core.py."""

    @pytest.fixture
    def tmp_kb(self, tmp_path, monkeypatch):
        """Create a temporary KB directory with sample entries."""
        kb_path = tmp_path / "kb"
        kb_path.mkdir()
        (kb_path / ".kbconfig").write_text("""
kb_path: .
memory_evolution:
  enabled: true
  model: test-model
  min_score: 0.7
""")
        (kb_path / ".indices").mkdir()
        (kb_path / "test").mkdir()

        # Create a new entry
        (kb_path / "test" / "new.md").write_text("""---
title: New Entry
tags: [testing]
keywords: [new-concept]
created: 2024-01-15T10:00:00+00:00
---

# New Entry

Content about new concepts.
""")

        # Create a neighbor entry
        (kb_path / "test" / "neighbor.md").write_text("""---
title: Neighbor Entry
tags: [existing]
keywords: [old-concept]
created: 2024-01-14T10:00:00+00:00
---

# Neighbor Entry

Content about existing concepts.
""")

        monkeypatch.setenv("MEMEX_SKIP_PROJECT_KB", "")
        monkeypatch.chdir(kb_path)

        return kb_path

    @pytest.mark.asyncio
    async def test_process_evolution_disabled(self, tmp_kb, monkeypatch):
        """Processing returns early when evolution is disabled."""
        monkeypatch.setattr(
            "memex.core.get_memory_evolution_config",
            lambda: MemoryEvolutionConfig(enabled=False),
        )

        from memex.evolution_queue import QueueItem
        from datetime import datetime, UTC

        items = [QueueItem(
            new_entry="test/new.md",
            neighbor="test/neighbor.md",
            score=0.8,
            queued_at=datetime.now(UTC),
        )]

        result = await core.process_evolution_items(items, tmp_kb)
        assert result.processed == 0
        assert result.keywords_added == 0

    @pytest.mark.asyncio
    async def test_process_evolution_with_mock_llm(self, tmp_kb, monkeypatch):
        """Processing applies LLM suggestions to neighbors (replacement semantics)."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        # Mock the LLM to return complete new keyword list (use proper dataclass)
        mock_suggestion = EvolutionSuggestion(
            neighbor_path="test/neighbor.md",
            new_keywords=["old-concept", "new-keyword"],  # Complete replacement list
            relationship="Related to new concepts",
            new_context="",  # No description update
        )

        async def mock_evolve(*args, **kwargs):
            return [mock_suggestion]

        with patch("memex.llm.evolve_neighbors_batched", mock_evolve):
            from memex.evolution_queue import QueueItem
            from datetime import datetime, UTC

            items = [QueueItem(
                new_entry="test/new.md",
                neighbor="test/neighbor.md",
                score=0.8,
                queued_at=datetime.now(UTC),
            )]

            result = await core.process_evolution_items(items, tmp_kb)

        assert result.processed == 1
        assert result.keywords_added == 1  # One new keyword added

        # Verify neighbor was updated with complete replacement
        neighbor_content = (tmp_kb / "test" / "neighbor.md").read_text()
        assert "new-keyword" in neighbor_content
        assert "old-concept" in neighbor_content

    @pytest.mark.asyncio
    async def test_process_evolution_updates_description(self, tmp_kb, monkeypatch):
        """Processing applies LLM-suggested description (new_context) to neighbors."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        # Mock the LLM to return new keywords AND new_context
        mock_suggestion = EvolutionSuggestion(
            neighbor_path="test/neighbor.md",
            new_keywords=["old-concept", "evolved-keyword"],
            relationship="Related to new concepts",
            new_context="A comprehensive guide to existing concepts and their evolution.",
        )

        async def mock_evolve(*args, **kwargs):
            return [mock_suggestion]

        with patch("memex.llm.evolve_neighbors_batched", mock_evolve):
            from memex.evolution_queue import QueueItem
            from datetime import datetime, UTC

            items = [QueueItem(
                new_entry="test/new.md",
                neighbor="test/neighbor.md",
                score=0.8,
                queued_at=datetime.now(UTC),
            )]

            result = await core.process_evolution_items(items, tmp_kb)

        assert result.processed == 1

        # Verify neighbor was updated with description
        neighbor_content = (tmp_kb / "test" / "neighbor.md").read_text()
        assert "evolved-keyword" in neighbor_content
        assert "description: A comprehensive guide to existing concepts" in neighbor_content

    @pytest.mark.asyncio
    async def test_process_evolution_preserves_description_when_empty_context(self, tmp_kb, monkeypatch):
        """Empty new_context from LLM preserves existing description."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        # Create neighbor with existing description
        (tmp_kb / "test" / "neighbor.md").write_text("""---
title: Neighbor Entry
description: Original description that should be preserved.
tags: [existing]
keywords: [old-concept]
created: 2024-01-14T10:00:00+00:00
---

# Neighbor Entry

Content about existing concepts.
""")

        # Mock the LLM to return new keywords but EMPTY new_context
        mock_suggestion = EvolutionSuggestion(
            neighbor_path="test/neighbor.md",
            new_keywords=["old-concept", "another-keyword"],
            relationship="Related",
            new_context="",  # Empty - should preserve existing description
        )

        async def mock_evolve(*args, **kwargs):
            return [mock_suggestion]

        with patch("memex.llm.evolve_neighbors_batched", mock_evolve):
            from memex.evolution_queue import QueueItem
            from datetime import datetime, UTC

            items = [QueueItem(
                new_entry="test/new.md",
                neighbor="test/neighbor.md",
                score=0.8,
                queued_at=datetime.now(UTC),
            )]

            result = await core.process_evolution_items(items, tmp_kb)

        assert result.processed == 1

        # Verify original description was preserved
        neighbor_content = (tmp_kb / "test" / "neighbor.md").read_text()
        assert "another-keyword" in neighbor_content
        assert "Original description that should be preserved" in neighbor_content

    @pytest.mark.asyncio
    async def test_process_evolution_description_only_update(self, tmp_kb, monkeypatch):
        """Evolution can update just description when keywords unchanged."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        # Mock the LLM to return SAME keywords but NEW context
        mock_suggestion = EvolutionSuggestion(
            neighbor_path="test/neighbor.md",
            new_keywords=["old-concept"],  # Same as existing
            relationship="",
            new_context="New semantic description for this entry.",
        )

        async def mock_evolve(*args, **kwargs):
            return [mock_suggestion]

        with patch("memex.llm.evolve_neighbors_batched", mock_evolve):
            from memex.evolution_queue import QueueItem
            from datetime import datetime, UTC

            items = [QueueItem(
                new_entry="test/new.md",
                neighbor="test/neighbor.md",
                score=0.8,
                queued_at=datetime.now(UTC),
            )]

            result = await core.process_evolution_items(items, tmp_kb)

        # Should still process because description changed
        assert result.processed == 1
        assert result.keywords_added == 0  # No new keywords

        # Verify description was updated
        neighbor_content = (tmp_kb / "test" / "neighbor.md").read_text()
        assert "description: New semantic description for this entry" in neighbor_content

    @pytest.mark.asyncio
    async def test_process_evolution_records_history(self, tmp_kb, monkeypatch):
        """Evolution records history with before/after values."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        # Mock the LLM to return new keywords and description
        mock_suggestion = EvolutionSuggestion(
            neighbor_path="test/neighbor.md",
            new_keywords=["old-concept", "evolved-keyword"],
            relationship="",
            new_context="Updated description from evolution.",
        )

        async def mock_evolve(*args, **kwargs):
            return [mock_suggestion]

        with patch("memex.llm.evolve_neighbors_batched", mock_evolve):
            from memex.evolution_queue import QueueItem
            from datetime import datetime, UTC

            items = [QueueItem(
                new_entry="test/new.md",
                neighbor="test/neighbor.md",
                score=0.8,
                queued_at=datetime.now(UTC),
            )]

            await core.process_evolution_items(items, tmp_kb)

        # Verify history was recorded
        neighbor_content = (tmp_kb / "test" / "neighbor.md").read_text()
        assert "evolution_history:" in neighbor_content
        assert "trigger_entry: test/new.md" in neighbor_content
        assert "previous_keywords:" in neighbor_content
        assert "old-concept" in neighbor_content
        assert "new_keywords:" in neighbor_content
        assert "evolved-keyword" in neighbor_content
        assert "new_description: Updated description from evolution" in neighbor_content

    @pytest.mark.asyncio
    async def test_evolution_history_accumulates(self, tmp_kb, monkeypatch):
        """Multiple evolutions accumulate in history."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        # First evolution
        mock_suggestion1 = EvolutionSuggestion(
            neighbor_path="test/neighbor.md",
            new_keywords=["old-concept", "keyword-from-first"],
            relationship="",
            new_context="",
        )

        async def mock_evolve1(*args, **kwargs):
            return [mock_suggestion1]

        with patch("memex.llm.evolve_neighbors_batched", mock_evolve1):
            from memex.evolution_queue import QueueItem
            from datetime import datetime, UTC

            items = [QueueItem(
                new_entry="test/first-trigger.md",
                neighbor="test/neighbor.md",
                score=0.8,
                queued_at=datetime.now(UTC),
            )]

            # Create the trigger entry first
            (tmp_kb / "test" / "first-trigger.md").write_text("""---
title: First Trigger
tags: [testing]
keywords: [first-trigger-kw]
created: 2024-01-16T10:00:00+00:00
---

# First Trigger
""")

            await core.process_evolution_items(items, tmp_kb)

        # Second evolution
        mock_suggestion2 = EvolutionSuggestion(
            neighbor_path="test/neighbor.md",
            new_keywords=["old-concept", "keyword-from-first", "keyword-from-second"],
            relationship="",
            new_context="",
        )

        async def mock_evolve2(*args, **kwargs):
            return [mock_suggestion2]

        with patch("memex.llm.evolve_neighbors_batched", mock_evolve2):
            items = [QueueItem(
                new_entry="test/second-trigger.md",
                neighbor="test/neighbor.md",
                score=0.9,
                queued_at=datetime.now(UTC),
            )]

            # Create the second trigger entry
            (tmp_kb / "test" / "second-trigger.md").write_text("""---
title: Second Trigger
tags: [testing]
keywords: [second-trigger-kw]
created: 2024-01-17T10:00:00+00:00
---

# Second Trigger
""")

            await core.process_evolution_items(items, tmp_kb)

        # Verify both history records exist
        neighbor_content = (tmp_kb / "test" / "neighbor.md").read_text()
        assert "trigger_entry: test/first-trigger.md" in neighbor_content
        assert "trigger_entry: test/second-trigger.md" in neighbor_content

    @pytest.mark.asyncio
    async def test_evolution_history_correct_before_after_values(self, tmp_kb, monkeypatch):
        """History records correct before and after values for keywords."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        # Set up neighbor with specific initial keywords
        (tmp_kb / "test" / "neighbor.md").write_text("""---
title: Neighbor Entry
description: Original description
tags: [existing]
keywords: [alpha, beta]
created: 2024-01-14T10:00:00+00:00
---

# Neighbor Entry

Content about existing concepts.
""")

        mock_suggestion = EvolutionSuggestion(
            neighbor_path="test/neighbor.md",
            new_keywords=["alpha", "beta", "gamma"],  # Added gamma
            relationship="",
            new_context="Enhanced description.",
        )

        async def mock_evolve(*args, **kwargs):
            return [mock_suggestion]

        with patch("memex.llm.evolve_neighbors_batched", mock_evolve):
            from memex.evolution_queue import QueueItem
            from datetime import datetime, UTC

            items = [QueueItem(
                new_entry="test/new.md",
                neighbor="test/neighbor.md",
                score=0.85,
                queued_at=datetime.now(UTC),
            )]

            await core.process_evolution_items(items, tmp_kb)

        # Parse the result to verify history contents
        from memex.parser import parse_entry

        metadata, _, _ = parse_entry(tmp_kb / "test" / "neighbor.md")
        assert len(metadata.evolution_history) == 1

        record = metadata.evolution_history[0]
        assert record.trigger_entry == "test/new.md"
        assert set(record.previous_keywords) == {"alpha", "beta"}
        assert set(record.new_keywords) == {"alpha", "beta", "gamma"}
        assert record.previous_description == "Original description"
        assert record.new_description == "Enhanced description."
class TestStrengthenAction:
    """Tests for the strengthen action (updating new entry based on neighbors)."""

    @pytest.mark.asyncio
    async def test_analyze_for_strengthen_no_neighbors(self, monkeypatch):
        """analyze_for_strengthen returns no changes with empty neighbors."""
        from memex.llm import analyze_for_strengthen

        result = await analyze_for_strengthen(
            new_entry_content="Test content",
            new_entry_keywords=["test"],
            new_entry_title="Test Entry",
            neighbors=[],
            model="test-model",
        )

        assert result.should_strengthen is False
        assert result.new_keywords == ["test"]
        assert result.suggested_links == []

    @pytest.mark.asyncio
    async def test_analyze_for_strengthen_parses_response(self, monkeypatch):
        """analyze_for_strengthen correctly parses LLM response."""
        from memex.llm import NeighborInfo, StrengthenResult, analyze_for_strengthen

        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "should_strengthen": True,
                        "new_keywords": ["test", "python", "automation"],
                        "suggested_links": ["guides/python.md"]
                    })
                )
            )
        ]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("memex.llm._get_openai_client", return_value=mock_client):
            neighbors = [
                NeighborInfo(
                    path="guides/python.md",
                    title="Python Guide",
                    content="Guide about Python programming",
                    keywords=["python"],
                    score=0.85
                )
            ]

            result = await analyze_for_strengthen(
                new_entry_content="Content about test automation",
                new_entry_keywords=["test"],
                new_entry_title="Test Automation",
                neighbors=neighbors,
                model="test-model",
            )

        assert result.should_strengthen is True
        assert result.new_keywords == ["test", "python", "automation"]
        assert result.suggested_links == ["guides/python.md"]

    @pytest.mark.asyncio
    async def test_analyze_for_strengthen_should_not_strengthen(self, monkeypatch):
        """analyze_for_strengthen respects should_strengthen=false."""
        from memex.llm import NeighborInfo, analyze_for_strengthen

        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "should_strengthen": False,
                        "new_keywords": ["test"],  # Same as input
                        "suggested_links": []
                    })
                )
            )
        ]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("memex.llm._get_openai_client", return_value=mock_client):
            neighbors = [
                NeighborInfo(
                    path="guides/python.md",
                    title="Python",
                    content="Python content",
                    keywords=["python"],
                    score=0.75
                )
            ]

            result = await analyze_for_strengthen(
                new_entry_content="Test content",
                new_entry_keywords=["test"],
                new_entry_title="Test",
                neighbors=neighbors,
                model="test-model",
            )

        assert result.should_strengthen is False
        assert result.new_keywords == ["test"]

    @pytest.mark.asyncio
    async def test_analyze_for_strengthen_handles_invalid_json(self, monkeypatch):
        """analyze_for_strengthen handles invalid JSON gracefully."""
        from memex.llm import NeighborInfo, analyze_for_strengthen

        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="not valid json"))]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("memex.llm._get_openai_client", return_value=mock_client):
            neighbors = [NeighborInfo(path="test.md", title="Test", content="Content", keywords=["existing"], score=0.8)]

            result = await analyze_for_strengthen(
                new_entry_content="Content",
                new_entry_keywords=["original"],
                new_entry_title="Test",
                neighbors=neighbors,
                model="test-model",
            )

        # Preserves original keywords on error
        assert result.should_strengthen is False
        assert result.new_keywords == ["original"]
        assert result.suggested_links == []

    @pytest.mark.asyncio
    async def test_analyze_for_strengthen_filters_invalid_links(self, monkeypatch):
        """analyze_for_strengthen filters out links not in neighbor list."""
        from memex.llm import NeighborInfo, analyze_for_strengthen

        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "should_strengthen": True,
                        "new_keywords": ["test", "new"],
                        "suggested_links": [
                            "valid/neighbor.md",
                            "invalid/not-a-neighbor.md",  # Not in neighbors list
                        ]
                    })
                )
            )
        ]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("memex.llm._get_openai_client", return_value=mock_client):
            neighbors = [
                NeighborInfo(path="valid/neighbor.md", title="Valid", content="Content", keywords=["test"], score=0.8)
            ]

            result = await analyze_for_strengthen(
                new_entry_content="Content",
                new_entry_keywords=["test"],
                new_entry_title="Test",
                neighbors=neighbors,
                model="test-model",
            )

        # Only valid neighbor path should be in suggested links
        assert result.suggested_links == ["valid/neighbor.md"]


class TestStrengthenConfig:
    """Tests for strengthen_on_add configuration."""

    def test_default_config_strengthen_disabled(self, tmp_path, monkeypatch):
        """Default config has strengthen_on_add disabled (conservative default)."""
        monkeypatch.chdir(tmp_path)
        config = get_memory_evolution_config()
        assert config.strengthen_on_add is False

    def test_config_loads_strengthen_on_add(self, tmp_path, monkeypatch):
        """Config loads strengthen_on_add from .kbconfig."""
        kbconfig = tmp_path / ".kbconfig"
        kb_path = tmp_path / "kb"
        kb_path.mkdir()
        kbconfig.write_text(
            """
kb_path: kb
memory_evolution:
  enabled: true
  strengthen_on_add: true
"""
        )
        monkeypatch.chdir(tmp_path)

        config = get_memory_evolution_config()
        assert config.enabled is True
        assert config.strengthen_on_add is True

    def test_config_strengthen_explicit_false(self, tmp_path, monkeypatch):
        """Config respects strengthen_on_add: false."""
        kbconfig = tmp_path / ".kbconfig"
        kb_path = tmp_path / "kb"
        kb_path.mkdir()
        kbconfig.write_text(
            """
kb_path: kb
memory_evolution:
  enabled: true
  strengthen_on_add: false
"""
        )
        monkeypatch.chdir(tmp_path)

        config = get_memory_evolution_config()
        assert config.enabled is True
        assert config.strengthen_on_add is False
