"""Tests for CLI argument validation."""

from click.testing import CliRunner

from memex.cli import cli


class TestSearchLimitValidation:
    """Tests for search command --limit option validation."""

    def test_search_limit_zero_shows_error(self):
        """--limit 0 should show a clean error, not a traceback."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test", "--limit", "0"])
        assert result.exit_code != 0
        assert "0 is not in the range x>=1" in result.output or "0 is not in the range" in result.output

    def test_search_limit_negative_shows_error(self):
        """--limit -1 should show a clean error, not a traceback."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test", "--limit", "-1"])
        assert result.exit_code != 0
        assert "-1 is not in the range x>=1" in result.output or "-1 is not in the range" in result.output

    def test_search_limit_positive_accepted(self):
        """--limit with positive values should be accepted (validation passes)."""
        runner = CliRunner()
        # We just check that the validation passes - the command may fail
        # for other reasons (no KB configured) but that's fine
        result = runner.invoke(cli, ["search", "test", "--limit", "1"])
        # Should not contain IntRange validation error
        assert "is not in the range" not in result.output

    def test_search_limit_large_positive_accepted(self):
        """--limit with large positive values should be accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "test", "--limit", "100"])
        assert "is not in the range" not in result.output
