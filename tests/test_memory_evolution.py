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
