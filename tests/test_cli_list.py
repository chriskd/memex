"""Tests for mx list CLI command."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from memex import core
from memex.cli import cli


@pytest.fixture(autouse=True)
def reset_searcher_state(monkeypatch):
    """Ensure cached searcher state does not leak across tests."""
    monkeypatch.setattr(core, "_searcher", None)
    monkeypatch.setattr(core, "_searcher_ready", False)


@pytest.fixture
def kb_root(tmp_path, monkeypatch) -> Path:
    """Create a temporary KB root with standard categories."""
    root = tmp_path / "kb"
    root.mkdir()
    for category in ("development", "architecture", "devops"):
        (root / category).mkdir()
    monkeypatch.setenv("MEMEX_KB_ROOT", str(root))
    return root


@pytest.fixture
def index_root(tmp_path, monkeypatch) -> Path:
    """Create a temporary index root."""
    root = tmp_path / ".indices"
    root.mkdir()
    monkeypatch.setenv("MEMEX_INDEX_ROOT", str(root))
    return root


def _create_entry(
    path: Path,
    title: str,
    tags: list[str],
    created: datetime,
):
    """Helper to create a KB entry with frontmatter."""
    tags_yaml = "\n".join(f"  - {tag}" for tag in tags)
    content = f"""---
title: {title}
tags:
{tags_yaml}
created: {created.isoformat()}
---

## Content

Some content here.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


class TestListCommandCategoryValidation:
    """Test mx list --category validation."""

    def test_list_invalid_category_shows_helpful_error(self, kb_root, index_root):
        """Invalid category shows error with valid categories listed."""
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--category=nonexistent"])

        assert result.exit_code == 1
        assert "Error: Invalid category 'nonexistent'" in result.output
        assert "Valid categories:" in result.output
        # Should list actual categories
        assert "architecture" in result.output
        assert "development" in result.output
        assert "devops" in result.output

    def test_list_invalid_category_no_traceback(self, kb_root, index_root):
        """Invalid category does not produce a Python traceback."""
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--category=nonexistent"])

        assert result.exit_code == 1
        # Should not contain traceback indicators
        assert "Traceback" not in result.output
        assert "ValueError" not in result.output
        assert "File \"" not in result.output

    def test_list_valid_category_works(self, kb_root, index_root):
        """Valid category returns entries from that category."""
        today = datetime.now(timezone.utc)
        _create_entry(
            kb_root / "development" / "entry.md",
            "Dev Entry",
            ["python"],
            created=today,
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--category=development"])

        assert result.exit_code == 0
        assert "Dev Entry" in result.output

    def test_list_valid_category_no_entries(self, kb_root, index_root):
        """Valid but empty category shows 'No entries found'."""
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--category=architecture"])

        assert result.exit_code == 0
        assert "No entries found" in result.output

    def test_list_no_category_lists_all(self, kb_root, index_root):
        """Without category filter, lists all entries."""
        today = datetime.now(timezone.utc)
        _create_entry(
            kb_root / "development" / "dev.md",
            "Dev Entry",
            ["python"],
            created=today,
        )
        _create_entry(
            kb_root / "architecture" / "arch.md",
            "Arch Entry",
            ["design"],
            created=today,
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["list"])

        assert result.exit_code == 0
        assert "Dev Entry" in result.output
        assert "Arch Entry" in result.output

    def test_list_empty_kb_shows_no_categories(self, tmp_path, monkeypatch):
        """When KB has no categories, error message says so."""
        # Create an empty KB root
        empty_root = tmp_path / "empty_kb"
        empty_root.mkdir()
        monkeypatch.setenv("MEMEX_KB_ROOT", str(empty_root))

        # Reset searcher to pick up new root
        monkeypatch.setattr(core, "_searcher", None)
        monkeypatch.setattr(core, "_searcher_ready", False)

        runner = CliRunner()
        result = runner.invoke(cli, ["list", "--category=nonexistent"])

        assert result.exit_code == 1
        assert "Error: Invalid category 'nonexistent'" in result.output
        assert "No categories exist yet" in result.output
