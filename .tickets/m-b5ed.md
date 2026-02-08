---
id: m-b5ed
status: closed
deps: []
links: []
created: 2026-02-08T04:25:44Z
type: task
priority: 2
assignee: chriskd
---
# Onboarding: add mx categories + better mx add category guidance

New users and agents frequently need to discover available categories quickly. Today this is only discoverable via `mx info`/`mx tree`, and `mx add` warnings do not list what exists.

## Acceptance Criteria

- Add `mx categories` command to list top-level category directories, show primary, and support `--json` + `--scope`
- `mx add` warning for missing `--category` mentions `mx categories` and (best-effort) lists available categories
- `mx add --category=<new>` warns before auto-creating a new category/directory (helps catch typos)
- Update `mx schema` output to include `categories`

## Notes

**2026-02-08T04:30:28Z**

Added `mx categories` (with `--json` and `--scope`) to list category directories and show primary. Improved `mx add` warnings: missing `--category` now points to `mx categories` and lists available categories (best-effort), and providing a new `--category` warns before creating a new directory. Updated schema to include `categories` and `eval` options. Added CLI tests for `mx categories`. Files: `src/memex/cli.py`, `tests/test_cli.py`, `kb/reference/cli.md`, `README.md`.
