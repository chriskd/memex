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
  max_keywords_per_neighbor: 5
"""
        )
        monkeypatch.chdir(tmp_path)

        config = get_memory_evolution_config()
        assert config.enabled is True
        assert config.model == "openai/gpt-4o-mini"
        assert config.min_score == 0.8
        assert config.max_keywords_per_neighbor == 5

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
                        {"add_keywords": ["python", "testing"], "relationship": "Related to testing concepts"}
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
                max_keywords=3,
            )

        assert result.neighbor_path == "guides/python.md"
        assert result.add_keywords == ["testing"]  # python filtered as existing
        assert result.relationship == "Related to testing concepts"

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
                neighbor_keywords=[],
                link_score=0.8,
                model="test-model",
            )

        assert result.add_keywords == []
        assert result.relationship == ""

    @pytest.mark.asyncio
    async def test_evolve_neighbors_batched_single_neighbor(self, monkeypatch):
        """evolve_neighbors_batched uses single-neighbor path for 1 neighbor."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=json.dumps({"add_keywords": ["new"], "relationship": "test"})))
        ]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("memex.llm._get_openai_client", return_value=mock_client):
            neighbors = [NeighborInfo(path="test.md", title="Test", content="Content", keywords=[], score=0.8)]

            results = await evolve_neighbors_batched(
                new_entry_title="New Entry",
                new_entry_content="New content",
                new_entry_keywords=["new"],
                neighbors=neighbors,
                model="test-model",
            )

        assert len(results) == 1
        assert results[0].add_keywords == ["new"]

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
                            {"path": "a.md", "add_keywords": ["kw1"], "relationship": "rel1"},
                            {"path": "b.md", "add_keywords": ["kw2"], "relationship": "rel2"},
                        ]
                    )
                )
            )
        ]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("memex.llm._get_openai_client", return_value=mock_client):
            neighbors = [
                NeighborInfo(path="a.md", title="A", content="Content A", keywords=[], score=0.8),
                NeighborInfo(path="b.md", title="B", content="Content B", keywords=[], score=0.75),
            ]

            results = await evolve_neighbors_batched(
                new_entry_title="New",
                new_entry_content="Content",
                new_entry_keywords=[],
                neighbors=neighbors,
                model="test-model",
            )

        assert len(results) == 2
        assert results[0].add_keywords == ["kw1"]
        assert results[1].add_keywords == ["kw2"]

    @pytest.mark.asyncio
    async def test_evolve_neighbors_filters_existing_keywords(self, monkeypatch):
        """Keywords already in neighbor are filtered out."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {"add_keywords": ["existing", "new", "EXISTING"], "relationship": ""}  # uppercase dupe
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
                neighbor_keywords=["existing"],  # Already has "existing"
                link_score=0.8,
                model="test-model",
            )

        # Only "new" should be added (existing and EXISTING filtered)
        assert result.add_keywords == ["new"]


class TestEvolveNeighborsIntegration:
    """Integration tests for _evolve_neighbors in core.py."""

    @pytest.fixture
    def tmp_kb(self, tmp_path, monkeypatch):
        """Create a temporary KB directory."""
        kb_path = tmp_path / "kb"
        kb_path.mkdir()
        (kb_path / ".kbconfig").write_text("kb_path: .")
        (kb_path / "test").mkdir()

        # Set up environment
        monkeypatch.setenv("MEMEX_SKIP_PROJECT_KB", "")
        monkeypatch.chdir(kb_path)

        return kb_path

    @pytest.mark.asyncio
    async def test_evolve_neighbors_skipped_when_disabled(self, tmp_kb, monkeypatch):
        """Evolution is skipped when disabled in config."""
        # Ensure evolution is disabled (default)
        monkeypatch.setattr(
            "memex.core.get_memory_evolution_config",
            lambda: MemoryEvolutionConfig(enabled=False),
        )

        # Should not raise, just skip
        await core._evolve_neighbors(
            new_entry_title="Test",
            new_entry_content="Content",
            new_entry_keywords=[],
            neighbors_to_evolve=[("test/neighbor.md", 0.8)],
            kb_root=tmp_kb,
            searcher=MagicMock(),
        )
        # No assertions - just verifying it doesn't error

    @pytest.mark.asyncio
    async def test_evolve_neighbors_filters_by_min_score(self, tmp_kb, monkeypatch):
        """Only neighbors below min_score are filtered out."""
        monkeypatch.setattr(
            "memex.core.get_memory_evolution_config",
            lambda: MemoryEvolutionConfig(enabled=True, min_score=0.8),
        )
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        # All neighbors below threshold - should skip evolution entirely
        # (no file parsing needed since filtered by score first)
        await core._evolve_neighbors(
            new_entry_title="Test",
            new_entry_content="Content",
            new_entry_keywords=[],
            neighbors_to_evolve=[("test/a.md", 0.7), ("test/b.md", 0.6)],  # Below 0.8
            kb_root=tmp_kb,
            searcher=MagicMock(),
        )
        # Test passes if no errors raised - neighbors were filtered by score
