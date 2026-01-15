"""Tests for A-Mem strict mode enforcement.

When amem_strict: true is set in .kbconfig, add_entry() and update_entry()
require keywords to improve semantic linking effectiveness.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from memex import core
from memex.config import (
    AMEM_STRICT_ERROR_MESSAGE,
    AMEMStrictError,
    is_amem_strict_enabled,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def project_with_amem_strict(tmp_path: Path):
    """Create a project directory with amem_strict enabled in .kbconfig."""
    # Create .kbconfig with amem_strict enabled
    kbconfig = tmp_path / ".kbconfig"
    kbconfig.write_text("""kb_path: kb
amem_strict: true
""")

    # Create the KB directory
    kb_path = tmp_path / "kb"
    kb_path.mkdir()
    (kb_path / "general").mkdir()

    # Create a kbconfig.yaml in the KB for categories
    (kb_path / "kbconfig.yaml").write_text("""categories:
  - name: general
    path: general
    description: General entries
""")

    return tmp_path


@pytest.fixture
def project_without_amem_strict(tmp_path: Path):
    """Create a project directory without amem_strict in .kbconfig."""
    # Create .kbconfig without amem_strict
    kbconfig = tmp_path / ".kbconfig"
    kbconfig.write_text("""kb_path: kb
""")

    # Create the KB directory
    kb_path = tmp_path / "kb"
    kb_path.mkdir()
    (kb_path / "general").mkdir()

    # Create a kbconfig.yaml in the KB for categories
    (kb_path / "kbconfig.yaml").write_text("""categories:
  - name: general
    path: general
    description: General entries
""")

    return tmp_path


# ─────────────────────────────────────────────────────────────────────────────
# Config Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestIsAmemStrictEnabled:
    """Tests for is_amem_strict_enabled() config function."""

    def test_returns_false_when_no_kbconfig(self, tmp_path: Path, monkeypatch):
        """Returns False when no .kbconfig exists."""
        monkeypatch.chdir(tmp_path)
        assert is_amem_strict_enabled() is False

    def test_returns_false_when_not_set(self, project_without_amem_strict: Path, monkeypatch):
        """Returns False when amem_strict not in .kbconfig."""
        monkeypatch.chdir(project_without_amem_strict)
        assert is_amem_strict_enabled() is False

    def test_returns_true_when_enabled(self, project_with_amem_strict: Path, monkeypatch):
        """Returns True when amem_strict: true in .kbconfig."""
        monkeypatch.chdir(project_with_amem_strict)
        assert is_amem_strict_enabled() is True

    def test_returns_false_when_explicitly_disabled(self, tmp_path: Path, monkeypatch):
        """Returns False when amem_strict: false in .kbconfig."""
        kbconfig = tmp_path / ".kbconfig"
        kbconfig.write_text("""kb_path: kb
amem_strict: false
""")
        (tmp_path / "kb").mkdir()
        monkeypatch.chdir(tmp_path)
        assert is_amem_strict_enabled() is False


# ─────────────────────────────────────────────────────────────────────────────
# Add Entry Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAddEntryAmemStrict:
    """Tests for add_entry with amem_strict mode."""

    @pytest.fixture(autouse=True)
    def reset_searcher_state(self, monkeypatch):
        """Ensure cached searcher state does not leak across tests."""
        monkeypatch.setattr(core, "_searcher", None)
        monkeypatch.setattr(core, "_searcher_ready", False)

    @pytest.mark.asyncio
    async def test_add_without_keywords_fails_when_strict(
        self, project_with_amem_strict: Path, monkeypatch
    ):
        """add_entry without keywords raises AMEMStrictError when strict mode enabled."""
        monkeypatch.chdir(project_with_amem_strict)
        # Disable project KB skip to use our test project
        monkeypatch.delenv("MEMEX_SKIP_PROJECT_KB", raising=False)
        monkeypatch.delenv("MEMEX_USER_KB_ROOT", raising=False)

        with pytest.raises(AMEMStrictError) as exc_info:
            await core.add_entry(
                title="Test Entry",
                content="Some content",
                tags=["test"],
                category="general",
            )

        # Verify the error message is helpful
        assert "--keywords" in str(exc_info.value)
        assert "mx add" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_with_keywords_succeeds_when_strict(
        self, project_with_amem_strict: Path, monkeypatch
    ):
        """add_entry with keywords succeeds when strict mode enabled."""
        monkeypatch.chdir(project_with_amem_strict)
        monkeypatch.delenv("MEMEX_SKIP_PROJECT_KB", raising=False)
        monkeypatch.delenv("MEMEX_USER_KB_ROOT", raising=False)

        result = await core.add_entry(
            title="Test Entry",
            content="Some content about REST APIs",
            tags=["test"],
            category="general",
            keywords=["REST", "API", "web"],
        )

        assert "path" in result
        assert result["path"].endswith(".md")

    @pytest.mark.asyncio
    async def test_add_without_keywords_succeeds_when_not_strict(
        self, project_without_amem_strict: Path, monkeypatch
    ):
        """add_entry without keywords succeeds when strict mode disabled."""
        monkeypatch.chdir(project_without_amem_strict)
        monkeypatch.delenv("MEMEX_SKIP_PROJECT_KB", raising=False)
        monkeypatch.delenv("MEMEX_USER_KB_ROOT", raising=False)

        result = await core.add_entry(
            title="Test Entry",
            content="Some content",
            tags=["test"],
            category="general",
        )

        assert "path" in result


# ─────────────────────────────────────────────────────────────────────────────
# Update Entry Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestUpdateEntryAmemStrict:
    """Tests for update_entry with amem_strict mode."""

    @pytest.fixture(autouse=True)
    def reset_searcher_state(self, monkeypatch):
        """Ensure cached searcher state does not leak across tests."""
        monkeypatch.setattr(core, "_searcher", None)
        monkeypatch.setattr(core, "_searcher_ready", False)

    def _create_entry(self, kb_path: Path, has_keywords: bool = False):
        """Create a test entry."""
        entry_path = kb_path / "general" / "test-entry.md"
        entry_path.parent.mkdir(parents=True, exist_ok=True)

        keywords_line = "keywords: [existing, concepts]\n" if has_keywords else ""
        entry_path.write_text(f"""---
title: Test Entry
tags: [test]
{keywords_line}created: 2024-01-15
---

Original content.
""")
        return "general/test-entry.md"

    @pytest.mark.asyncio
    async def test_update_content_without_keywords_fails_when_strict(
        self, project_with_amem_strict: Path, monkeypatch
    ):
        """update_entry with content change but no keywords raises AMEMStrictError."""
        monkeypatch.chdir(project_with_amem_strict)
        monkeypatch.delenv("MEMEX_SKIP_PROJECT_KB", raising=False)
        monkeypatch.delenv("MEMEX_USER_KB_ROOT", raising=False)

        kb_path = project_with_amem_strict / "kb"
        entry_rel_path = self._create_entry(kb_path, has_keywords=False)

        with pytest.raises(AMEMStrictError):
            await core.update_entry(
                path=entry_rel_path,
                content="Updated content without keywords",
            )

    @pytest.mark.asyncio
    async def test_update_content_with_keywords_succeeds_when_strict(
        self, project_with_amem_strict: Path, monkeypatch
    ):
        """update_entry with content change and keywords succeeds."""
        monkeypatch.chdir(project_with_amem_strict)
        monkeypatch.delenv("MEMEX_SKIP_PROJECT_KB", raising=False)
        monkeypatch.delenv("MEMEX_USER_KB_ROOT", raising=False)

        kb_path = project_with_amem_strict / "kb"
        entry_rel_path = self._create_entry(kb_path, has_keywords=False)

        result = await core.update_entry(
            path=entry_rel_path,
            content="Updated content with keywords",
            keywords=["new", "concepts"],
        )

        assert "path" in result

    @pytest.mark.asyncio
    async def test_update_content_succeeds_when_entry_has_keywords(
        self, project_with_amem_strict: Path, monkeypatch
    ):
        """update_entry with content change succeeds if entry already has keywords."""
        monkeypatch.chdir(project_with_amem_strict)
        monkeypatch.delenv("MEMEX_SKIP_PROJECT_KB", raising=False)
        monkeypatch.delenv("MEMEX_USER_KB_ROOT", raising=False)

        kb_path = project_with_amem_strict / "kb"
        entry_rel_path = self._create_entry(kb_path, has_keywords=True)

        result = await core.update_entry(
            path=entry_rel_path,
            content="Updated content - entry already has keywords",
        )

        assert "path" in result

    @pytest.mark.asyncio
    async def test_update_tags_only_succeeds_without_keywords(
        self, project_with_amem_strict: Path, monkeypatch
    ):
        """update_entry with only tag changes succeeds without keywords."""
        monkeypatch.chdir(project_with_amem_strict)
        monkeypatch.delenv("MEMEX_SKIP_PROJECT_KB", raising=False)
        monkeypatch.delenv("MEMEX_USER_KB_ROOT", raising=False)

        kb_path = project_with_amem_strict / "kb"
        entry_rel_path = self._create_entry(kb_path, has_keywords=False)

        # Tag-only update shouldn't require keywords
        result = await core.update_entry(
            path=entry_rel_path,
            tags=["updated", "tags"],
        )

        assert "path" in result


# ─────────────────────────────────────────────────────────────────────────────
# Error Message Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestErrorMessage:
    """Tests for the helpful error message."""

    def test_error_message_contains_example_command(self):
        """Error message shows example mx add command with --keywords."""
        assert "mx add" in AMEM_STRICT_ERROR_MESSAGE
        assert "--keywords" in AMEM_STRICT_ERROR_MESSAGE

    def test_error_message_explains_good_keywords(self):
        """Error message explains what good keywords look like."""
        assert "concept" in AMEM_STRICT_ERROR_MESSAGE.lower()
        assert "3-7" in AMEM_STRICT_ERROR_MESSAGE

    def test_error_message_tells_how_to_disable(self):
        """Error message explains how to disable strict mode."""
        assert "amem_strict: false" in AMEM_STRICT_ERROR_MESSAGE
        assert ".kbconfig" in AMEM_STRICT_ERROR_MESSAGE

    def test_amem_strict_error_is_value_error(self):
        """AMEMStrictError inherits from ValueError for CLI compatibility."""
        assert issubclass(AMEMStrictError, ValueError)


# ─────────────────────────────────────────────────────────────────────────────
# CLI Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCLIAmemStrict:
    """Tests for CLI error display with amem_strict mode."""

    def test_cli_add_shows_helpful_error(
        self, project_with_amem_strict: Path, runner, monkeypatch
    ):
        """CLI displays the full error message when add fails due to strict mode."""
        from click.testing import CliRunner
        from memex.cli import cli

        monkeypatch.chdir(project_with_amem_strict)
        monkeypatch.delenv("MEMEX_SKIP_PROJECT_KB", raising=False)
        monkeypatch.delenv("MEMEX_USER_KB_ROOT", raising=False)

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "add",
                "--title=Test Entry",
                "--tags=test",
                "--category=general",
                "--content=Some content",
            ],
        )

        assert result.exit_code == 1
        assert "--keywords" in result.output
        assert "mx add" in result.output
        assert "amem_strict: false" in result.output
