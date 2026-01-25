---
id: m-4c9c
status: open
deps: []
links: []
created: 2026-01-25T06:39:57Z
type: task
priority: 2
assignee: chriskd
---
# Investigate semantic/hybrid search startup latency

Perf sanity: hybrid/semantic search ~5-6s on small (~15 file) KB, keyword search ~1.5s. Likely heavy startup cost (embedding/model load).

## Acceptance Criteria

- [ ] Identify root cause of per-invocation latency (profiling/notes)\n- [ ] Implement mitigation (cache/model reuse/daemon/batch)\n- [ ] Document before/after timings

