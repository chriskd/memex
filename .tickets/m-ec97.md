---
id: m-ec97
status: closed
deps: []
links: []
created: 2026-02-08T04:25:44Z
type: task
priority: 2
assignee: chriskd
---
# Onboarding: show full paths in table outputs (list/search)

Agents need exact entry paths for `mx get`, `mx delete`, etc. Truncating `PATH` values in table output forces extra round trips (re-run with `--terse` or `--json`) and slows cold-start onboarding.

## Acceptance Criteria

- `mx list` table output never truncates entry paths by default
- `mx search` table output never truncates entry paths by default (neighbor and non-neighbor modes)
- Title truncation remains the default (with `--full-titles` to expand)
- Any "Tip" text refers to titles only (paths are already full)

## Notes

**2026-02-08T04:30:28Z**

Removed PATH truncation in table outputs by default by making `format_table` treat `path` as unbounded unless explicitly capped, and removing explicit path caps in `mx search`, `mx list`, `mx whats-new`, `mx hubs`, and `mx history --rerun`. Added CLI test to ensure search table includes full paths. Files: `src/memex/cli.py`, `tests/test_cli.py`.
