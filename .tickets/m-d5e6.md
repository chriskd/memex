---
id: m-d5e6
status: closed
deps: []
links: []
created: 2026-02-08T07:11:58Z
type: feature
priority: 2
assignee: chriskd
---
# mx add: warn on implicit category; silence via .kbconfig

Remove "category required" friction while still nudging users/agents to organize entries intentionally.

## Acceptance Criteria

- `mx add` does not require `--category`
- When `--category` is omitted and `.kbconfig primary` is not set, print a warning by default
- Allow silencing this warning with `.kbconfig` flag (`warn_on_implicit_category: false`)
- `mx init` does not set a default `primary` automatically
- Tests

## Notes

**2026-02-08T07:11:58Z**

- Added `.kbconfig` flag `warn_on_implicit_category` (default true)
- `mx add` respects the flag for the "defaulting to KB root" warning
- `mx init` no longer writes `primary: inbox` by default (keeps `# primary: inbox` commented)
- Added `mx context show` visibility for the flag
- Updated README config example
- Tests updated/added: `tests/test_cli.py`

