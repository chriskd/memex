---
title: Semantic Linking
tags:
  - a-mem
  - semantic-links
  - features
created: 2026-01-14T23:27:03.555183+00:00
updated: 2026-01-15T02:55:14.820116+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
semantic_links:
  - path: reference/dense-memory-signals-research.md
    score: 0.62
    reason: embedding_similarity
  - path: a-mem-parity/graph-aware-search.md
    score: 0.836
    reason: bidirectional
  - path: a-mem-parity/keywords-and-embeddings.md
    score: 0.625
    reason: bidirectional
  - path: a-mem-parity/a-mem-parity-analysis.md
    score: 0.671
    reason: bidirectional
  - path: a-mem-parity/entry-metadata-schema.md
    score: 0.683
    reason: bidirectional
  - path: a-mem-parity/a-mem-init-command-specification.md
    score: 0.67
    reason: bidirectional
---

# Semantic Linking

Memex implements A-Mem-style semantic linking: automatic discovery and maintenance of relationships between entries based on embedding similarity.

## Overview

When entries are added or updated, memex automatically:
1. Computes embedding similarity with existing entries
2. Creates forward links to similar entries (reason: `embedding_similarity`)
3. Creates backlinks from those entries (reason: `bidirectional`)

This enables graph-aware search and knowledge discovery.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `SEMANTIC_LINK_ENABLED` | `True` | Enable/disable auto-linking |
| `SEMANTIC_LINK_MIN_SCORE` | `0.6` | Minimum similarity threshold (0-1) |
| `SEMANTIC_LINK_K` | `5` | Maximum neighbors to link |

## CLI Flags

### Adding entries with links

```bash
# Auto-linking happens automatically on add/update
mx add --title="Python Guide" --tags="python" --content="..."

# Manual links (skips auto-linking)
mx add --title="Entry" --semantic-links="other.md:0.9:manual" --content="..."
```

### Graph-aware search

```bash
# Include semantically linked entries in results
mx search "query" --include-neighbors

# Control traversal depth (default: 1, max: 5)
mx search "query" --include-neighbors --neighbor-depth=2
```

## Output Formats

### JSON output with neighbors

```json
{
  "results": [
    {"path": "guides/python.md", "score": 0.85, "is_neighbor": false},
    {"path": "ref/typing.md", "score": 0.72, "is_neighbor": true, "linked_from": "guides/python.md"}
  ]
}
```

### Table output

Neighbors are marked with `*` in the `NBR` column.

### Terse output

Neighbors are prefixed with `[N]`.

## SemanticLink Model

```python
class SemanticLink(BaseModel):
    path: str      # Target entry path
    score: float   # Similarity score (0-1)
    reason: str    # 'embedding_similarity' | 'bidirectional' | 'shared_tags'
```

## How It Works

1. **On add_entry/update_entry**: After indexing, find top-k similar entries
2. **Filter**: Only keep results above `SEMANTIC_LINK_MIN_SCORE`
3. **Forward link**: Add `SemanticLink` to new entry with reason `embedding_similarity`
4. **Backlink**: Add `SemanticLink` to neighbor with reason `bidirectional`
5. **Re-index**: Update affected entries in the search index

## Edge Cases

- **Self-linking**: Entries never link to themselves
- **Duplicate prevention**: Backlinks are not duplicated on repeated updates
- **Manual links**: When `semantic_links` is provided manually, auto-linking is skipped
- **Tags-only updates**: Content-less updates skip auto-linking
- **Missing neighbors**: Graph traversal gracefully skips missing files
- **Circular links**: BFS traversal handles cycles without infinite loops