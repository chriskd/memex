"""Tests for A-Mem init command (Phase 1: Inventory & Validation).

Tests cover:
- Entry inventory with chronological sorting
- Missing keyword detection and modes
- Scope filtering (project/user)
- CLI command output
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from memex import core
from memex.cli import cli

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


def create_test_entry(
    kb_root: Path,
    path: str,
    title: str,
    created: str,
    tags: list[str] | None = None,
    keywords: list[str] | None = None,
) -> Path:
    """Create a test entry with specific metadata."""
    entry_path = kb_root / path
    entry_path.parent.mkdir(parents=True, exist_ok=True)

    tags_str = f"[{', '.join(tags)}]" if tags else "[test]"
    keywords_line = f"keywords: [{', '.join(keywords)}]" if keywords else ""

    frontmatter = f"""---
title: {title}
tags: {tags_str}
created: {created}
{keywords_line}
---

# {title}

Content for {title}.
"""
    entry_path.write_text(frontmatter)
    return entry_path


@pytest.fixture
def kb_with_mixed_entries(tmp_kb: Path) -> Path:
    """KB with entries having various keyword states and created dates."""
    # Oldest entry - has keywords
    create_test_entry(
        tmp_kb,
        "guides/first-guide.md",
        "First Guide",
        "2024-01-01T10:00:00Z",
        tags=["guide"],
        keywords=["getting-started", "introduction"],
    )

    # Second entry - no keywords
    create_test_entry(
        tmp_kb,
        "reference/api-docs.md",
        "API Documentation",
        "2024-01-15T14:30:00Z",
        tags=["api", "reference"],
        keywords=None,
    )

    # Third entry - has keywords
    create_test_entry(
        tmp_kb,
        "tutorials/advanced-tutorial.md",
        "Advanced Tutorial",
        "2024-02-01T09:00:00Z",
        tags=["tutorial"],
        keywords=["advanced", "patterns"],
    )

    # Fourth entry - no keywords
    create_test_entry(
        tmp_kb,
        "notes/quick-note.md",
        "Quick Note",
        "2024-03-01T16:00:00Z",
        tags=["notes"],
        keywords=None,
    )

    return tmp_kb


@pytest.fixture
def kb_all_with_keywords(tmp_kb: Path) -> Path:
    """KB where all entries have keywords."""
    create_test_entry(
        tmp_kb,
        "entry-a.md",
        "Entry A",
        "2024-01-01T10:00:00Z",
        keywords=["keyword-a"],
    )
    create_test_entry(
        tmp_kb,
        "entry-b.md",
        "Entry B",
        "2024-02-01T10:00:00Z",
        keywords=["keyword-b"],
    )
    return tmp_kb


@pytest.fixture
def project_with_amem_strict(tmp_path: Path) -> Path:
    """Create a project directory with amem_strict enabled."""
    kbconfig = tmp_path / ".kbconfig"
    kbconfig.write_text("""kb_path: kb
amem_strict: true
""")

    kb_path = tmp_path / "kb"
    kb_path.mkdir()

    (kb_path / "kbconfig.yaml").write_text("""categories:
  - name: general
    path: .
    description: General entries
""")

    return tmp_path


# ─────────────────────────────────────────────────────────────────────────────
# Core Function Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAmemInitInventory:
    """Tests for amem_init_inventory() core function."""

    @pytest.mark.asyncio
    async def test_returns_empty_result_when_no_kb(self, tmp_path: Path, monkeypatch):
        """Returns empty result when no KB exists."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("MEMEX_USER_KB_ROOT", str(tmp_path / "nonexistent"))
        monkeypatch.setenv("MEMEX_SKIP_PROJECT_KB", "1")

        result = await core.amem_init_inventory()

        assert result.total_count == 0
        assert result.entries == []

    @pytest.mark.asyncio
    async def test_sorts_entries_chronologically(self, kb_with_mixed_entries: Path):
        """Entries are sorted by created timestamp, oldest first."""
        result = await core.amem_init_inventory()

        assert result.total_count == 4
        # Check chronological order
        assert result.entries[0].title == "First Guide"  # 2024-01-01
        assert result.entries[1].title == "API Documentation"  # 2024-01-15
        assert result.entries[2].title == "Advanced Tutorial"  # 2024-02-01
        assert result.entries[3].title == "Quick Note"  # 2024-03-01

    @pytest.mark.asyncio
    async def test_detects_missing_keywords(self, kb_with_mixed_entries: Path):
        """Correctly identifies entries with and without keywords."""
        result = await core.amem_init_inventory()

        assert result.with_keywords == 2
        assert result.missing_keywords == 2

        # Check individual entries
        with_kw = [e for e in result.entries if e.has_keywords]
        without_kw = [e for e in result.entries if not e.has_keywords]

        assert len(with_kw) == 2
        assert len(without_kw) == 2

    @pytest.mark.asyncio
    async def test_skip_mode_marks_entries_as_skipped(self, kb_with_mixed_entries: Path):
        """Skip mode marks entries without keywords as skipped."""
        result = await core.amem_init_inventory(missing_keywords="skip")

        assert result.missing_keyword_mode == "skip"
        assert result.skipped_count == 2

        skipped = [e for e in result.entries if e.keyword_status == "skipped"]
        assert len(skipped) == 2

    @pytest.mark.asyncio
    async def test_llm_mode_marks_entries_as_needs_llm(self, kb_with_mixed_entries: Path):
        """LLM mode marks entries without keywords as needs_llm."""
        result = await core.amem_init_inventory(missing_keywords="llm")

        assert result.missing_keyword_mode == "llm"
        assert result.needs_llm_count == 2

        needs_llm = [e for e in result.entries if e.keyword_status == "needs_llm"]
        assert len(needs_llm) == 2

    @pytest.mark.asyncio
    async def test_error_mode_populates_errors_list(self, kb_with_mixed_entries: Path):
        """Error mode adds entries without keywords to errors list."""
        result = await core.amem_init_inventory(missing_keywords="error")

        assert result.missing_keyword_mode == "error"
        assert len(result.errors) == 2

        # Errors should contain paths
        assert any("api-docs.md" in e for e in result.errors)
        assert any("quick-note.md" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_limit_parameter_restricts_results(self, kb_with_mixed_entries: Path):
        """Limit parameter restricts number of entries returned."""
        result = await core.amem_init_inventory(limit=2)

        assert result.total_count == 2
        assert len(result.entries) == 2
        # Should be the oldest two entries
        assert result.entries[0].title == "First Guide"
        assert result.entries[1].title == "API Documentation"

    @pytest.mark.asyncio
    async def test_entries_include_absolute_path(self, kb_with_mixed_entries: Path):
        """Entries include absolute_path for file operations."""
        result = await core.amem_init_inventory()

        for entry in result.entries:
            assert entry.absolute_path is not None
            assert Path(entry.absolute_path).exists()

    @pytest.mark.asyncio
    async def test_entries_include_existing_keywords(self, kb_with_mixed_entries: Path):
        """Entries with keywords include the keyword list."""
        result = await core.amem_init_inventory()

        first_guide = next(e for e in result.entries if e.title == "First Guide")
        assert first_guide.keywords == ["getting-started", "introduction"]

        api_docs = next(e for e in result.entries if e.title == "API Documentation")
        assert api_docs.keywords == []

    @pytest.mark.asyncio
    async def test_default_mode_uses_skip_when_amem_strict_disabled(
        self, kb_with_mixed_entries: Path
    ):
        """Default mode is skip when amem_strict is not enabled."""
        result = await core.amem_init_inventory(missing_keywords=None)

        assert result.missing_keyword_mode == "skip"

    @pytest.mark.asyncio
    async def test_default_mode_uses_error_when_amem_strict_enabled(
        self, project_with_amem_strict: Path, monkeypatch
    ):
        """Default mode is error when amem_strict is enabled."""
        monkeypatch.chdir(project_with_amem_strict)
        monkeypatch.delenv("MEMEX_SKIP_PROJECT_KB", raising=False)
        monkeypatch.delenv("MEMEX_USER_KB_ROOT", raising=False)

        # Clear cached context
        from memex.context import _context_cache
        _context_cache.clear()

        # Create test entry without keywords
        kb_path = project_with_amem_strict / "kb"
        create_test_entry(
            kb_path,
            "test.md",
            "Test Entry",
            "2024-01-01T10:00:00Z",
            keywords=None,
        )

        result = await core.amem_init_inventory(missing_keywords=None)

        assert result.missing_keyword_mode == "error"

    @pytest.mark.asyncio
    async def test_all_entries_with_keywords_reports_correctly(
        self, kb_all_with_keywords: Path
    ):
        """Reports correctly when all entries have keywords."""
        result = await core.amem_init_inventory()

        assert result.total_count == 2
        assert result.with_keywords == 2
        assert result.missing_keywords == 0
        assert result.errors == []


# ─────────────────────────────────────────────────────────────────────────────
# CLI Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAmemInitCLI:
    """Tests for mx a-mem-init CLI command."""

    def test_help_shows_command_options(self, runner: CliRunner):
        """Help text includes all options."""
        result = runner.invoke(cli, ["a-mem-init", "--help"])

        assert result.exit_code == 0
        assert "--missing-keywords" in result.output
        assert "--scope" in result.output
        assert "--dry-run" in result.output
        assert "--limit" in result.output
        assert "--json" in result.output

    def test_dry_run_shows_preview(self, runner: CliRunner, kb_with_mixed_entries: Path):
        """Dry run shows preview of what would happen."""
        result = runner.invoke(
            cli,
            ["a-mem-init", "--dry-run"],
            env={"MEMEX_USER_KB_ROOT": str(kb_with_mixed_entries)},
        )

        assert result.exit_code == 0
        assert "dry run" in result.output.lower()
        assert "Entries found:" in result.output
        assert "Processing order" in result.output

    def test_json_output_format(self, runner: CliRunner, kb_with_mixed_entries: Path):
        """JSON output includes all expected fields."""
        result = runner.invoke(
            cli,
            ["a-mem-init", "--json", "--missing-keywords=skip"],
            env={"MEMEX_USER_KB_ROOT": str(kb_with_mixed_entries)},
        )

        assert result.exit_code == 0
        data = json.loads(result.output)

        assert data["phase"] == "inventory"
        assert data["total_count"] == 4
        assert data["with_keywords"] == 2
        assert data["missing_keywords"] == 2
        assert data["mode"] == "skip"
        assert len(data["entries"]) == 4

    def test_error_mode_exits_with_error_when_missing_keywords(
        self, runner: CliRunner, kb_with_mixed_entries: Path
    ):
        """Error mode exits with code 1 when entries are missing keywords."""
        result = runner.invoke(
            cli,
            ["a-mem-init", "--missing-keywords=error"],
            env={"MEMEX_USER_KB_ROOT": str(kb_with_mixed_entries)},
        )

        assert result.exit_code == 1
        assert "Error:" in result.output or "missing keywords" in result.output

    def test_skip_mode_succeeds_with_missing_keywords(
        self, runner: CliRunner, kb_with_mixed_entries: Path
    ):
        """Skip mode succeeds even when entries are missing keywords."""
        result = runner.invoke(
            cli,
            ["a-mem-init", "--missing-keywords=skip"],
            env={"MEMEX_USER_KB_ROOT": str(kb_with_mixed_entries)},
        )

        assert result.exit_code == 0
        assert "will skip" in result.output

    def test_limit_parameter_restricts_processing(
        self, runner: CliRunner, kb_with_mixed_entries: Path
    ):
        """Limit parameter restricts entries processed."""
        result = runner.invoke(
            cli,
            ["a-mem-init", "--json", "--limit=2"],
            env={"MEMEX_USER_KB_ROOT": str(kb_with_mixed_entries)},
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_count"] == 2

    def test_all_keywords_present_shows_success(
        self, runner: CliRunner, kb_all_with_keywords: Path
    ):
        """When all entries have keywords, shows success message."""
        result = runner.invoke(
            cli,
            ["a-mem-init"],
            env={"MEMEX_USER_KB_ROOT": str(kb_all_with_keywords)},
        )

        assert result.exit_code == 0
        assert "Inventory complete" in result.output


# ─────────────────────────────────────────────────────────────────────────────
# Scope Filtering Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAmemInitScopeFiltering:
    """Tests for scope filtering in a-mem-init."""

    @pytest.mark.asyncio
    async def test_scope_project_filters_to_project_kb_only(
        self, project_with_amem_strict: Path, monkeypatch
    ):
        """Scope=project only includes project KB entries."""
        monkeypatch.chdir(project_with_amem_strict)
        monkeypatch.delenv("MEMEX_SKIP_PROJECT_KB", raising=False)
        monkeypatch.delenv("MEMEX_USER_KB_ROOT", raising=False)

        from memex.context import _context_cache
        _context_cache.clear()

        # Create entry in project KB
        kb_path = project_with_amem_strict / "kb"
        create_test_entry(
            kb_path,
            "project-entry.md",
            "Project Entry",
            "2024-01-01T10:00:00Z",
            keywords=["project"],
        )

        result = await core.amem_init_inventory(scope="project")

        assert result.total_count == 1
        assert result.entries[0].title == "Project Entry"


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: LLM Keyword Extraction Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAmemInitKeywordExtraction:
    """Tests for Phase 2: LLM keyword extraction."""

    @pytest.mark.asyncio
    async def test_no_entries_needing_llm_returns_empty_result(
        self, kb_all_with_keywords: Path
    ):
        """Returns empty result when no entries need LLM extraction."""
        inventory = await core.amem_init_inventory(missing_keywords="llm")

        result = await core.amem_init_extract_keywords(inventory)

        assert result.entries_processed == 0
        assert result.entries_updated == 0
        assert result.entries_failed == 0

    @pytest.mark.asyncio
    async def test_extracts_keywords_and_updates_entry(
        self, kb_with_mixed_entries: Path, monkeypatch
    ):
        """Successfully extracts keywords and updates entry frontmatter."""
        from memex.llm import KeywordExtractionResult

        # Mock the LLM call
        async def mock_extract(*args, **kwargs):
            return KeywordExtractionResult(
                keywords=["api", "rest", "documentation"],
                success=True,
            )

        monkeypatch.setattr("memex.llm.extract_keywords_llm", mock_extract)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        inventory = await core.amem_init_inventory(missing_keywords="llm")
        assert inventory.needs_llm_count == 2  # Two entries need keywords

        result = await core.amem_init_extract_keywords(inventory, model="test-model")

        assert result.entries_processed == 2
        assert result.entries_updated == 2
        assert result.entries_failed == 0

        # Verify keywords were written to file
        from memex.parser import parse_entry
        api_docs_path = kb_with_mixed_entries / "reference/api-docs.md"
        metadata, _, _ = parse_entry(api_docs_path)
        assert set(metadata.keywords) == {"api", "rest", "documentation"}

    @pytest.mark.asyncio
    async def test_handles_llm_extraction_failure(
        self, kb_with_mixed_entries: Path, monkeypatch
    ):
        """Records failure when LLM extraction fails."""
        from memex.llm import KeywordExtractionResult

        # Mock failing LLM call
        async def mock_extract_fail(*args, **kwargs):
            return KeywordExtractionResult(
                keywords=[],
                success=False,
                error="API rate limit exceeded",
            )

        monkeypatch.setattr("memex.llm.extract_keywords_llm", mock_extract_fail)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        inventory = await core.amem_init_inventory(missing_keywords="llm")
        result = await core.amem_init_extract_keywords(inventory, model="test-model")

        assert result.entries_processed == 2
        assert result.entries_updated == 0
        assert result.entries_failed == 2
        assert len(result.errors) == 2
        assert any("API rate limit" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_continues_processing_after_single_failure(
        self, kb_with_mixed_entries: Path, monkeypatch
    ):
        """Continues processing other entries after one fails."""
        from memex.llm import KeywordExtractionResult

        call_count = 0

        # First call fails, second succeeds
        async def mock_extract_mixed(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return KeywordExtractionResult(
                    keywords=[],
                    success=False,
                    error="Network error",
                )
            return KeywordExtractionResult(
                keywords=["keyword1", "keyword2"],
                success=True,
            )

        monkeypatch.setattr("memex.llm.extract_keywords_llm", mock_extract_mixed)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        inventory = await core.amem_init_inventory(missing_keywords="llm")
        result = await core.amem_init_extract_keywords(inventory, model="test-model")

        assert result.entries_processed == 2
        assert result.entries_updated == 1
        assert result.entries_failed == 1

    @pytest.mark.asyncio
    async def test_raises_on_llm_configuration_error(
        self, kb_with_mixed_entries: Path, monkeypatch
    ):
        """Raises LLMConfigurationError when API key not configured."""
        # Remove API key
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

        inventory = await core.amem_init_inventory(missing_keywords="llm")

        from memex.llm import LLMConfigurationError
        with pytest.raises(LLMConfigurationError):
            await core.amem_init_extract_keywords(inventory, model="test-model")

    @pytest.mark.asyncio
    async def test_uses_model_from_config_when_not_specified(
        self, kb_with_mixed_entries: Path, monkeypatch, tmp_path: Path
    ):
        """Uses memory_evolution.model from config when model not specified."""
        from memex.llm import KeywordExtractionResult

        captured_model = None

        async def mock_extract(content, title, model, **kwargs):
            nonlocal captured_model
            captured_model = model
            return KeywordExtractionResult(keywords=["test"], success=True)

        monkeypatch.setattr("memex.llm.extract_keywords_llm", mock_extract)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        # Create .kbconfig with model setting
        kbconfig = tmp_path / ".kbconfig"
        kbconfig.write_text("""kb_path: kb
memory_evolution:
  enabled: true
  model: anthropic/claude-3-5-sonnet
""")
        monkeypatch.chdir(tmp_path)

        # Clear cached context
        from memex.context import _context_cache
        _context_cache.clear()

        inventory = await core.amem_init_inventory(missing_keywords="llm")
        await core.amem_init_extract_keywords(inventory)  # No model specified

        assert captured_model == "anthropic/claude-3-5-sonnet"

    @pytest.mark.asyncio
    async def test_result_includes_extracted_keywords(
        self, kb_with_mixed_entries: Path, monkeypatch
    ):
        """Result includes the extracted keywords for each entry."""
        from memex.llm import KeywordExtractionResult

        async def mock_extract(*args, **kwargs):
            return KeywordExtractionResult(
                keywords=["extracted1", "extracted2"],
                success=True,
            )

        monkeypatch.setattr("memex.llm.extract_keywords_llm", mock_extract)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        inventory = await core.amem_init_inventory(missing_keywords="llm")
        result = await core.amem_init_extract_keywords(inventory, model="test-model")

        assert len(result.results) == 2
        for r in result.results:
            assert r.success is True
            assert r.keywords == ["extracted1", "extracted2"]


class TestExtractKeywordsLLM:
    """Tests for the LLM keyword extraction function."""

    @pytest.mark.asyncio
    async def test_extracts_keywords_successfully(self, monkeypatch):
        """Successfully extracts keywords from content."""
        from unittest.mock import AsyncMock, MagicMock

        # Mock OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"keywords": ["python", "async", "testing"]}'

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        def mock_get_client():
            return mock_client

        monkeypatch.setattr("memex.llm._get_openai_client", mock_get_client)

        from memex.llm import extract_keywords_llm
        result = await extract_keywords_llm(
            content="This is about Python async programming and testing patterns.",
            title="Python Async Guide",
            model="test-model",
        )

        assert result.success is True
        assert result.keywords == ["python", "async", "testing"]
        assert result.error is None

    @pytest.mark.asyncio
    async def test_handles_empty_keywords_response(self, monkeypatch):
        """Returns failure when LLM returns no keywords."""
        from unittest.mock import AsyncMock, MagicMock

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"keywords": []}'

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        def mock_get_client():
            return mock_client

        monkeypatch.setattr("memex.llm._get_openai_client", mock_get_client)

        from memex.llm import extract_keywords_llm
        result = await extract_keywords_llm(
            content="Some content",
            title="Test",
            model="test-model",
        )

        assert result.success is False
        assert result.keywords == []
        assert "no keywords" in result.error.lower()

    @pytest.mark.asyncio
    async def test_handles_json_parse_error(self, monkeypatch):
        """Returns failure on JSON parse error."""
        from unittest.mock import AsyncMock, MagicMock

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = 'not valid json'

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        def mock_get_client():
            return mock_client

        monkeypatch.setattr("memex.llm._get_openai_client", mock_get_client)

        from memex.llm import extract_keywords_llm
        result = await extract_keywords_llm(
            content="Some content",
            title="Test",
            model="test-model",
        )

        assert result.success is False
        assert "JSON parse error" in result.error

    @pytest.mark.asyncio
    async def test_normalizes_keywords_to_lowercase(self, monkeypatch):
        """Keywords are normalized to lowercase."""
        from unittest.mock import AsyncMock, MagicMock

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"keywords": ["Python", "ASYNC", "Testing"]}'

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        def mock_get_client():
            return mock_client

        monkeypatch.setattr("memex.llm._get_openai_client", mock_get_client)

        from memex.llm import extract_keywords_llm
        result = await extract_keywords_llm(
            content="Test content",
            title="Test",
            model="test-model",
        )

        assert result.keywords == ["python", "async", "testing"]

    @pytest.mark.asyncio
    async def test_respects_max_keywords_limit(self, monkeypatch):
        """Respects max_keywords parameter."""
        from unittest.mock import AsyncMock, MagicMock

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"keywords": ["a", "b", "c", "d", "e", "f", "g", "h"]}'

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        def mock_get_client():
            return mock_client

        monkeypatch.setattr("memex.llm._get_openai_client", mock_get_client)

        from memex.llm import extract_keywords_llm
        result = await extract_keywords_llm(
            content="Test content",
            title="Test",
            model="test-model",
            max_keywords=4,
        )

        assert len(result.keywords) == 4


class TestAmemInitCLIPhase2:
    """Tests for CLI with Phase 2 keyword extraction."""

    def test_llm_mode_shows_phase2_output(
        self, runner: CliRunner, kb_with_mixed_entries: Path, monkeypatch
    ):
        """LLM mode shows Phase 2 output when processing."""
        from memex.llm import KeywordExtractionResult

        async def mock_extract(*args, **kwargs):
            return KeywordExtractionResult(
                keywords=["extracted"],
                success=True,
            )

        monkeypatch.setattr("memex.llm.extract_keywords_llm", mock_extract)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        result = runner.invoke(
            cli,
            ["a-mem-init", "--missing-keywords=llm"],
            env={"MEMEX_USER_KB_ROOT": str(kb_with_mixed_entries)},
        )

        assert result.exit_code == 0
        assert "Phase 2: Keyword Extraction" in result.output
        assert "Updated:" in result.output

    def test_llm_mode_dry_run_does_not_run_phase2(
        self, runner: CliRunner, kb_with_mixed_entries: Path
    ):
        """Dry run does not execute Phase 2."""
        result = runner.invoke(
            cli,
            ["a-mem-init", "--missing-keywords=llm", "--dry-run"],
            env={"MEMEX_USER_KB_ROOT": str(kb_with_mixed_entries)},
        )

        assert result.exit_code == 0
        assert "Phase 2" not in result.output
        assert "will extract with LLM" in result.output

    def test_llm_mode_json_includes_phase2_results(
        self, runner: CliRunner, kb_with_mixed_entries: Path, monkeypatch
    ):
        """JSON output includes Phase 2 results."""
        from memex.llm import KeywordExtractionResult

        async def mock_extract(*args, **kwargs):
            return KeywordExtractionResult(
                keywords=["kw1", "kw2"],
                success=True,
            )

        monkeypatch.setattr("memex.llm.extract_keywords_llm", mock_extract)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        result = runner.invoke(
            cli,
            ["a-mem-init", "--missing-keywords=llm", "--json"],
            env={"MEMEX_USER_KB_ROOT": str(kb_with_mixed_entries)},
        )

        assert result.exit_code == 0
        data = json.loads(result.output)

        assert data["phase"] == "keyword_extraction"
        assert "phase2" in data
        assert data["phase2"]["entries_updated"] == 2

    def test_llm_config_error_shows_message(
        self, runner: CliRunner, kb_with_mixed_entries: Path, monkeypatch
    ):
        """Shows helpful message when LLM not configured."""
        # Ensure no API key is set
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

        result = runner.invoke(
            cli,
            ["a-mem-init", "--missing-keywords=llm"],
            env={"MEMEX_USER_KB_ROOT": str(kb_with_mixed_entries)},
        )

        assert result.exit_code == 1
        assert "OPENROUTER_API_KEY" in result.output or "LLM configuration error" in result.output
