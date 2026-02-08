---
id: mem-m9a8
status: in_progress
deps: []
links: []
created: 2026-02-08T08:48:07Z
type: chore
priority: 2
assignee: chriskd
tags: [gitignore, cleanup, publish]
---
# Stop tracking generated publish outputs

Remove generated publish artifacts (_site_repo, _first_run) from git and add ignores so test/publish runs don't dirty the repo.

## Acceptance Criteria

1) _site_repo/ and _first_run/ are removed from the repository\n2) .gitignore ignores _site/, _site_repo/, _first_run/\n3) git status stays clean after mx publish / first-run scripts (no accidental adds)

