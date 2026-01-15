---
title: Memory Evolution Queue Architecture
tags:
  - a-mem
  - architecture
  - design
created: 2026-01-15T00:29:27.310489+00:00
updated: 2026-01-15T00:56:26.004962+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
semantic_links:
  - path: reference/agent-memory-comparison.md
    score: 0.606
    reason: embedding_similarity
  - path: reference/memory-evolution-queue-architecture.md
    score: 0.845
    reason: bidirectional
---

# Memory Evolution Queue Architecture

Design for non-blocking, configurable memory evolution triggered via queue + manual command.

## Problem

The current implementation runs evolution inline during `add_entry()`, blocking the caller (often an LLM) until LLM API calls complete. This is unacceptable for interactive sessions.

## Solution: Queue + Manual Primitive

All evolution work is queued, never executed inline. A manual command processes the queue. Various triggers can invoke that command.

## Architecture

```
mx add ...  â  Queues evolution work (never blocks)
                    â
            .indices/evolution_queue.jsonl
                    â
            Processed by: mx evolve
                    â
            Triggered by:
              â¢ Manual: user/LLM runs mx evolve
              â¢ Hook: calls mx evolve on session end
              â¢ Probability: spawns background mx evolve
              â¢ Threshold: spawns background mx evolve when queue full
```

## Queue Format

File: `{kb_root}/.indices/evolution_queue.jsonl`

```jsonl
{"new_entry": "path/to/new.md", "neighbor": "path/to/neighbor.md", "score": 0.85, "queued_at": "2024-01-15T10:30:00Z"}
{"new_entry": "path/to/new.md", "neighbor": "path/to/other.md", "score": 0.72, "queued_at": "2024-01-15T10:30:00Z"}
```

Each line represents one neighbor that needs evolution analysis.

## CLI Commands

### mx evolve

Process queued evolution work.

```bash
mx evolve              # Process all queued items
mx evolve --dry-run    # Show what would be evolved
mx evolve --limit 10   # Process up to 10 items
mx evolve --status     # Show queue stats
```

### Behavior

1. Read queue file
2. Group by new_entry (batch neighbors for same entry)
3. Call LLM for each batch
4. Apply keyword updates to neighbors
5. Remove processed items from queue
6. Use file locking to prevent concurrent runs

## Configuration

```yaml
# .kbconfig
memory_evolution:
  enabled: true
  model: anthropic/claude-3-5-haiku
  min_score: 0.7
  max_keywords_per_neighbor: 3
  
  # Auto-trigger options (all optional)
  auto_probability: 0.0      # 0-1, chance to spawn evolve after add
  auto_queue_threshold: 0    # Spawn evolve when queue exceeds this size
```

## Trigger Mechanisms

### Manual (Always Available)

User or LLM runs `mx evolve` when convenient.

### Hook-Based

Example Claude Code hook (user configures):
```bash
# .claude/hooks/session-end.sh
mx evolve --limit 20 2>/dev/null || true
```

### Probability-Based (Built-in)

When `auto_probability > 0`:
1. After `mx add` completes, generate random float
2. If < probability, spawn `mx evolve` in background
3. Use `subprocess.Popen` with detached process
4. Parent returns immediately

### Queue Threshold (Built-in)

When `auto_queue_threshold > 0`:
1. After `mx add` queues work, count queue lines
2. If > threshold, spawn `mx evolve` in background
3. Same detached subprocess approach

## Implementation Changes

### core.py Changes

1. Remove `await _evolve_neighbors()` calls from `add_entry()` and `update_entry()`
2. Replace with `_queue_evolution()` that writes to queue file
3. Add `process_evolution_queue()` async function

### cli.py Changes

1. Add `mx evolve` command
2. Add auto-trigger logic at end of `add` command

### New: evolution_queue.py

Queue management utilities:
- `queue_evolution(new_entry, neighbors)` - Append to queue
- `read_queue()` - Read and parse queue
- `remove_from_queue(items)` - Remove processed items
- `queue_stats()` - Return count, oldest item, etc.

## File Locking

Use `fcntl.flock()` (Unix) or `msvcrt.locking()` (Windows) to prevent:
- Concurrent `mx evolve` runs corrupting queue
- Race between queue writes and reads

## Cost Considerations

With Haiku at ~$0.25/1M input tokens:
- Average prompt: ~800 tokens per neighbor
- Batching 5 neighbors: ~4,000 tokens
- Cost per batch: ~$0.001

Queue batching makes this efficient - processing 50 queued items in 10 batches costs ~$0.01.