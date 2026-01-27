---
id: m-bae1
status: closed
deps: []
links: [m-71f4]
created: 2026-01-25T06:47:23Z
type: task
priority: 2
assignee: chriskd
---
# Add state diagrams for major MX flows

Readiness review m-71f4 requires state diagrams for all major flows (init, add/update, search, typed relations, publish). Track as separate deliverable.

## Acceptance Criteria

- [x] State diagram for init + KB discovery (.kbconfig/.kbconfig)\n- [x] State diagram for add/update/patch flows (including category/primary rules)\n- [x] State diagram for search + neighbors/relations graph\n- [x] State diagram for typed relations add/remove + publish rendering\n- [x] Diagrams stored in KB or docs location and referenced from README/KB

## Notes

**2026-01-25T22:28:00Z**

Added kb/memex/state-diagrams.md with mermaid state diagrams for init/discovery, add/update, search/neighbors, and typed relations/publish. Linked from README and kb/reference/cli.md.
