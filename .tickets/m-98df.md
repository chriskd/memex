---
id: m-98df
status: closed
deps: []
links: []
created: 2026-02-08T00:22:54Z
type: feature
priority: 3
assignee: chriskd
---
# Agent UX: mx prime/session-context compact JSON

Agents want bounded-size machine output. Add --compact (structured fields only) and output-size controls for mx prime --json and/or mx session-context --json.

## Acceptance Criteria

- mx prime --json --compact omits large markdown 'content' and returns stable fields\n- Optional flags to bound size (max entries/recent/bytes)\n- Tests


## Notes

**2026-02-08T02:40:15Z**

Compact JSON + output bounds already implemented: mx prime --json --compact (--max-entries/--max-recent/--max-bytes) and mx session-context --json --compact (--max-bytes). Existing tests cover bounded machine-friendly output.
