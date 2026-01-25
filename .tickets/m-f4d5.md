---
id: m-f4d5
status: closed
deps: []
links: []
created: 2026-01-24T22:11:18Z
type: task
priority: 3
assignee: chriskd
---
# Improve publisher UX for typed relations

Render typed relations in published KB pages/graph (relation type labels, direction, filtering) so users can see relation semantics.

## Acceptance Criteria

- [ ] Relations display shows type labels and direction\n- [ ] Graph JSON includes relation type metadata\n- [ ] Docs updated to explain relation rendering


## Notes

**2026-01-25T05:56:00Z**

Implemented typed relations UI in publisher (entry panel + graph controls), normalized relation edges in graph.json, added tests and docs. Ran ruff check/format and pytest; pyright missing.
