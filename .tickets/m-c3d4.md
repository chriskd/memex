---
id: m-c3d4
status: closed
deps: []
links: []
created: 2026-02-08T07:11:58Z
type: docs
priority: 3
assignee: chriskd
---
# Docs: developer quick start + category warning flag

Reduce "from source" friction and make category behavior discoverable without reading code.

## Scope

- README: add a small "Developer quick start" section with `uv sync --dev` and `uv run mx ...`
- CLI docs: mention `.kbconfig warn_on_implicit_category` and when it matters

## Acceptance Criteria

- README includes a 3-command path to running mx from a repo checkout
- Docs describe category behavior:
  - no hard requirement for `--category`
  - warning when omitted and no `primary`
  - how to silence with `warn_on_implicit_category: false`

## Notes

**2026-02-08T07:25:05Z**

Updated `README.md` with a repo-checkout `uv run mx ...` note and documented `.kbconfig warn_on_implicit_category`. Updated `kb/reference/cli.md` to reflect that `--category` is optional and how to silence the warning.
