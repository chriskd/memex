---
id: m-b1c2
status: closed
deps: []
links: []
created: 2026-02-08T07:11:58Z
type: task
priority: 3
assignee: chriskd
---
# mx info: show search capability + missing deps

New users discover "semantic search missing" via runtime errors or only via `mx prime`. Make `mx info` a one-stop status readout.

## Acceptance Criteria

- `mx info` reports whether:
  - keyword search is available
  - semantic search is available
  - which optional deps are missing (if any) with install hint
- `mx info --json` includes stable boolean fields and a `missing_search_deps` list
- Add tests covering the "deps missing" state

## Notes

**2026-02-08T07:25:05Z**

`mx info` now reports keyword/semantic search availability, missing deps, and an install hint. `mx info --json` includes a stable `search` object with booleans and `missing_search_deps`. Covered in `tests/test_cli.py` smoke assertions.
