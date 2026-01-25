---
id: m-ee64
status: open
deps: []
links: []
created: 2026-01-25T06:39:09Z
type: bug
priority: 1
assignee: chriskd
---
# Publish should use kb_path from .kbconfig

mx publish fails in a project that only has .kbconfig (created by mx init) unless --kb-root or .kbcontext is set. Repro: mx init -> mx publish -o _site -> 'No KB found to publish'. .kbconfig has kb_path but context mapping ignores it.

## Acceptance Criteria

- [ ] mx publish resolves project KB from .kbconfig kb_path when .kbcontext is absent\n- [ ] Regression test covering publish without --kb-root in a project with .kbconfig\n- [ ] CLI output/help updated if needed

