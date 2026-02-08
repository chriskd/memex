---
id: m-cdad
status: closed
deps: []
links: []
created: 2026-02-08T00:22:54Z
type: task
priority: 3
assignee: chriskd
---
# mx init: README frontmatter + default primary

New KBs currently start with README frontmatter warnings and no default primary category. Improve default init template so the out-of-box KB is 'clean' and mx add does not warn.

## Acceptance Criteria

- kb/README.md created by mx init satisfies mx health frontmatter rules (or is excluded by default)\n- .kbconfig created by mx init sets a sensible default primary (e.g., inbox or guides)\n- docs updated if needed


## Notes

**2026-02-08T02:40:23Z**

mx init now creates default primary directory 'inbox' and writes primary: inbox into project/user .kbconfig so mx add doesn't warn on a fresh KB. Updated init test assertions. Files: src/memex/cli.py, tests/test_cli.py.
