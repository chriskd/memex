---
id: mem-822a
status: closed
deps: []
links: []
created: 2026-02-08T08:20:35Z
type: feature
priority: 2
assignee: chriskd
tags: [mx, onboarding, docs, cli]
---
# mx first-run onboarding improvements (cli+docs+kb indexes)

Implement items 1-6: improve missing-config guidance; make mx onboard best first command; add mx init --sample; improve unknown-command suggestions; add docs/README.md + update README.md; add kb reference indexes and ticket format reference.

## Acceptance Criteria

1) Running mx with no KB configured prints actionable next steps (onboard/init/doctor)\n2) mx onboard supports --yes and prints next commands\n3) mx init --sample creates a searchable sample entry\n4) Unknown command output shows top matches + help hints\n5) docs/README.md exists and README.md points to it\n6) kb/reference/index.md and kb/reference/tickets.md (or equivalent) exist


## Notes

**2026-02-08T08:27:21Z**

Starting implementation of onboarding improvements 1-6 (CLI error hints, init --sample, typo suggestions, docs + kb reference index/tickets).

**2026-02-08T08:35:54Z**

Implemented 1-6: CLI now standardizes ConfigurationError into KB_NOT_CONFIGURED with first-run guidance; status/doctor outputs show onboard/init/doctor + config locations; typo suggestions show top matches + help hints; added mx init --sample (creates inbox/first-task.md) and onboard --init now includes sample; added docs/README.md; added kb/reference/index.md + kb/reference/tickets.md; updated kb/guides/quick-start.md and README.md. Ran uv run pytest: 479 passed, 53 skipped.
