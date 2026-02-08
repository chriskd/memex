---
id: m-a0f1
status: closed
deps: []
links: []
created: 2026-02-08T07:11:58Z
type: feature
priority: 2
assignee: chriskd
---
# mx info: surface parse errors (paths + hints)

`mx info` reports `N parse errors` but does not say which entries failed to parse, which creates count mismatches vs `mx list` and slows down onboarding.

## Acceptance Criteria

- `mx info` includes a clear, actionable hint when parse errors exist (e.g., "Run: mx info --errors" or "Run: mx errors")
- New output mode lists parse errors with:
  - entry path
  - error type/message (truncated)
  - suggestion (common fixes: YAML frontmatter delimiter, invalid YAML, encoding)
- JSON output includes a structured `parse_errors` list with stable fields
- Add tests for at least one malformed entry

## Notes

**2026-02-08T07:25:05Z**

Implemented `mx info --errors` (with `--max-errors`) to show parse error paths + compact messages + fix hints. `mx info --json` now includes structured `parse_errors` and `parse_errors_truncated`. Added tests in `tests/test_cli.py`.
