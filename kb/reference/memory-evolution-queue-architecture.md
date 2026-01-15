---
title: Memory Evolution Queue Architecture
tags:
  - memex
  - architecture
  - memory-evolution
created: 2026-01-15T00:56:20.399983+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
git_branch: main
last_edited_by: chris
semantic_links:
  - path: a-mem-parity/memory-evolution-queue-architecture.md
    score: 0.845
    reason: embedding_similarity
  - path: reference/agent-memory-comparison.md
    score: 0.629
    reason: embedding_similarity
---

# Memory Evolution Queue Architecture

Non-blocking, queue-based memory evolution for memex. Replaces inline LLM calls during `mx add` with a producer-consumer pattern.

## Problem Solved

Previously, memory evolution ran inline during `add_entry()`, blocking callers (especially LLMs) until API calls completed. This was unacceptable for interactive sessions.

## Architecture

```
mx add  â  Queues evolution work (never blocks)
                    â
            .indices/evolution_queue.jsonl
                    â
            Processed by: mx evolve
                    â
            Triggered by:
              â¢ Manual: user/LLM runs mx evolve
              â¢ Hook: calls mx evolve on session end
              â¢ Probability: spawns background mx evolve
              â¢ Threshold: spawns when queue full
```

## Queue Format

File: `{kb_root}/.indices/evolution_queue.jsonl`

Each line is a JSON object:
```json
{"new_entry": "path/to/new.md", "neighbor": "path/to/neighbor.md", "score": 0.85, "queued_at": "2024-01-15T10:30:00Z"}
```

## CLI Commands

### mx evolve

Process queued evolution work:

```bash
mx evolve              # Process all queued items
mx evolve --status     # Show queue statistics
mx evolve --dry-run    # Show what would be evolved
mx evolve --limit 10   # Process up to 10 items
mx evolve --clear      # Clear all queued items
```

## Configuration

In `.kbconfig`:

```yaml
memory_evolution:
  enabled: true
  model: anthropic/claude-3-5-haiku
  min_score: 0.7
  max_keywords_per_neighbor: 3
  
  # Auto-trigger options
  auto_probability: 0.0      # 0-1, chance to spawn evolve after add
  auto_queue_threshold: 0    # Spawn evolve when queue exceeds this size
```

## Trigger Mechanisms

### Manual
User or LLM runs `mx evolve` when convenient.

### Hook-Based
Example Claude Code hook:
```bash
# .claude/hooks/session-end.sh
mx evolve --limit 20 2>/dev/null || true
```

### Probability-Based
When `auto_probability > 0`, after `mx add` completes there's a random chance to spawn `mx evolve` in background.

### Queue Threshold
When `auto_queue_threshold > 0` and queue exceeds that size, spawns background `mx evolve`.

## Implementation Files

- `src/memex/evolution_queue.py` - Queue management with file locking
- `src/memex/core.py` - `_queue_evolution()` and `process_evolution_items()`
- `src/memex/cli.py` - `mx evolve` command and `_maybe_trigger_evolution()`
- `src/memex/config.py` - `MemoryEvolutionConfig` with auto-trigger fields