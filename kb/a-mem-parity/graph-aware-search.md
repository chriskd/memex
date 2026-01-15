---
title: Graph-Aware Search
tags:
  - a-mem
  - search
  - graph-traversal
created: 2026-01-14T23:27:32.635652+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
git_branch: main
last_edited_by: chris
semantic_links:
  - path: a-mem-parity/semantic-linking.md
    score: 0.836
    reason: embedding_similarity
  - path: '@project/reference/cli.md'
    score: 0.668
    reason: embedding_similarity
  - path: '@project/guides/ai-integration.md'
    score: 0.617
    reason: embedding_similarity
---

# Graph-Aware Search

The `--include-neighbors` flag enables graph-aware search, expanding results by traversing semantic links.

## Basic Usage

```bash
# Standard search
mx search "machine learning"

# With neighbor expansion
mx search "machine learning" --include-neighbors

# Multi-hop traversal
mx search "machine learning" --include-neighbors --neighbor-depth=2
```

## How It Works

1. **Direct search**: Run normal hybrid/semantic/keyword search
2. **Neighbor expansion**: For each result, read its `semantic_links` field
3. **BFS traversal**: Follow links up to `--neighbor-depth` hops
4. **Deduplication**: Entries appearing via multiple paths only appear once
5. **Result marking**: Neighbors are flagged with `is_neighbor: true`

## Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--include-neighbors` | off | Enable graph traversal |
| `--neighbor-depth` | 1 | Hops to traverse (1-5) |

## Output Examples

### JSON

```bash
mx search "python" --include-neighbors --json
```

```json
{
  "results": [
    {
      "path": "guides/python-basics.md",
      "title": "Python Basics",
      "score": 0.89,
      "is_neighbor": false
    },
    {
      "path": "ref/type-hints.md",
      "title": "Type Hints Reference",
      "score": 0.75,
      "is_neighbor": true,
      "linked_from": "guides/python-basics.md"
    }
  ]
}
```

### Table

```
path                      title               score  conf  nbr
guides/python-basics.md   Python Basics       0.89   high
ref/type-hints.md         Type Hints Ref...   0.75   mod   *
```

### Terse

```bash
mx search "python" --include-neighbors --terse
```

```
guides/python-basics.md
[N] ref/type-hints.md
```

## Combining with Other Flags

```bash
# With content preview
mx search "api" --include-neighbors --content

# With score filtering
mx search "api" --include-neighbors --min-score=0.5

# With tag filtering
mx search "api" --include-neighbors --tags=reference
```

## Performance

- Neighbors are loaded lazily (only when expanding)
- Missing files are skipped gracefully
- Circular links are handled (no infinite loops)
- Depth is capped at 5 to prevent excessive traversal

## Use Cases

- **Knowledge discovery**: Find related concepts you didn't search for
- **Context gathering**: Collect all relevant entries for a topic
- **Dependency tracing**: See what an entry links to and from