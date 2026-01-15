---
title: A-Mem vs mx Implementation Audit
tags:
  - a-mem
  - audit
  - parity
  - architecture
created: 2026-01-15T03:42:58.597990+00:00
updated: 2026-01-15T05:42:49.128716+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
keywords:
  - implementation-comparison
  - evolution-semantics
  - tag-replacement
  - context-update
  - strengthen-action
semantic_links:
  - path: reference/agent-memory-comparison.md
    score: 0.803
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-parity-analysis.md
    score: 0.693
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-test-cases-for-agent-evaluation.md
    score: 0.693
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-init-command-specification.md
    score: 0.679
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-evaluation-methodology.md
    score: 0.667
    reason: embedding_similarity
  - path: memex/chunking-system-design.md
    score: 0.632
    reason: bidirectional
---

# A-Mem vs mx Implementation Audit

Comprehensive side-by-side comparison of the reference A-Mem implementation vs our mx implementation.

## Memory Structure

| Field | A-Mem | mx | Match? |
|-------|-------|-----|--------|
| Content | `content: str` | Markdown body | â |
| ID | `id: str` (UUID) | File path | â (different but OK) |
| Created | `timestamp: str` (YYYYMMDDHHMM) | `created: datetime` | â |
| Last accessed | `last_accessed: str` | `updated: datetime` | â |
| **Tags** | `tags: list[str]` | `tags: list[str]` | â |
| **Keywords** | `keywords: list[str]` | `keywords: list[str]` | â |
| **Context** | `context: str` (semantic role) | `description: str` | â (same concept) |
| Links | `links: list` (memory IDs) | `semantic_links: list[SemanticLink]` | â (richer) |
| Category | `category: str` | Directory path | â |
| Evolution history | `evolution_history: list` | Not tracked | â Missing |
| Retrieval count | `retrieval_count: int` | Not tracked | â Missing |

## Add Operation Flow

| Step | A-Mem | mx | Match? |
|------|-------|-----|--------|
| Create entry | `MemoryNote(content)` | Create file with frontmatter | â |
| **Evolution** | **SYNCHRONOUS** during add | Queued for later | â ï¸ Design choice |
| Index | Add to ChromaDB | Add to Whoosh + ChromaDB | â (we have more) |
| Return | Note ID | Entry path + suggestions | â |

## Evolution Trigger

| Aspect | A-Mem | mx | Match? |
|--------|-------|-----|--------|
| When | During `add_note()` (blocking) | Via `mx evolve` command (async) | â ï¸ Design choice |
| Decision | **LLM decides `should_evolve`** | Score threshold (>0.7) | â Different |
| Neighbors | `k=5` | `SEMANTIC_LINK_K=5` | â |

## Evolution Prompt Comparison

### A-Mem Prompt Structure
```python
"Based on this information, determine:
1. Should this memory be evolved?
2. What specific actions should be taken (strengthen, update_neighbor)?
   2.1 If strengthen: which memories to connect to? Updated tags for this memory?
   2.2 If update_neighbor: update context and tags of neighbors

Return JSON:
{
    "should_evolve": True or False,
    "actions": ["strengthen", "update_neighbor"],
    "suggested_connections": ["neighbor_ids"],
    "tags_to_update": ["tag1", "tag2"],  # For NEW entry
    "new_context_neighborhood": ["ctx1", "ctx2"],  # For neighbors
    "new_tags_neighborhood": [["t1"], ["t2"]]  # For neighbors
}"
```

### mx Prompt Structure
```python
"Based on this connection, suggest updates for the EXISTING entry:
1. 0-3 keywords to ADD (avoid duplicates)
2. One sentence describing this relationship

Respond with JSON:
{"add_keywords": ["kw1"], "relationship": "sentence"}"
```

### Prompt Differences

| Aspect | A-Mem | mx | Gap |
|--------|-------|-----|-----|
| **should_evolve** | LLM decides | Not asked | â Missing |
| **Actions** | strengthen, update_neighbor | Only update_neighbor equivalent | â Missing strengthen |
| **New entry updates** | `tags_to_update` | Not implemented | â Missing |
| **Neighbor tags** | `new_tags_neighborhood` (REPLACE) | `add_keywords` (APPEND) | â Wrong semantics |
| **Neighbor context** | `new_context_neighborhood` (REPLACE) | Not updated | â Missing |
| **Max limit** | None | `max_keywords_per_neighbor: 3` | â Artificial |

## Evolution Actions

### A-Mem "strengthen" Action
```python
if action == "strengthen":
    note.links.extend(suggested_connections)  # Add links to NEW entry
    note.tags = new_tags  # REPLACE NEW entry tags
```

**mx equivalent**: None. We never update the new entry after creation.

### A-Mem "update_neighbor" Action
```python
if action == "update_neighbor":
    for i, neighbor in enumerate(neighbors):
        neighbor.tags = new_tags_neighborhood[i]    # REPLACE
        neighbor.context = new_context_neighborhood[i]  # REPLACE
```

**mx equivalent**:
```python
# What we do:
new_keywords = [kw for kw in suggestion.add_keywords if kw not in existing]
updated_keywords = existing + new_keywords  # APPEND, not REPLACE
# We do NOT update description
```

## Critical Gaps (Must Fix)

### 1. Replace vs Append â
- **A-Mem**: `neighbor.tags = new_tags` (full replacement)
- **mx**: `keywords = existing + new_keywords` (append)
- **Impact**: Knowledge graph evolves completely differently

### 2. Context/Description Updates â
- **A-Mem**: Updates `neighbor.context` with new semantic role
- **mx**: Stores `relationship` but never updates neighbor's `description`
- **Impact**: Semantic understanding doesn't propagate

### 3. Strengthen Action â
- **A-Mem**: Updates NEW entry's tags + links based on neighbors
- **mx**: Never updates new entry after add
- **Impact**: New entries don't learn from existing knowledge

### 4. Max Keywords Cap â
- **A-Mem**: LLM decides appropriate tag count
- **mx**: Hardcoded `max_keywords_per_neighbor: 3`
- **Impact**: Artificial constraint on evolution

### 5. Should Evolve Decision â ï¸
- **A-Mem**: LLM decides if evolution makes sense
- **mx**: Score threshold (>0.7) decides
- **Impact**: Less nuanced, but probably OK

## What We Got Right â

1. **Queue-based evolution**: Arguably better than blocking - doesn't slow down `mx add`
2. **Bidirectional semantic links**: We track score + reason, A-Mem just stores IDs
3. **Hybrid search**: We have keyword (Whoosh) + semantic (ChromaDB), they only have semantic
4. **Persistent storage**: We use files (git-friendly), they use in-memory dict
5. **k=5 neighbors**: Same as A-Mem
6. **Consolidation equivalent**: Our `mx reindex` serves similar purpose

## Terminology Mapping

| A-Mem | mx | Notes |
|-------|-----|-------|
| `tags` | `keywords` | Same concept, different name |
| `context` | `description` | Same concept, different name |
| `links` | `semantic_links` | We have richer structure |
| `MemoryNote` | Entry (YAML frontmatter) | Same concept |
| `process_memory()` | `process_evolution_items()` | Same concept, different timing |

## Fix Priority

1. **P0**: Change append to replace for keywords/tags
2. **P0**: Add context/description updates
3. **P1**: Add strengthen action for new entries
4. **P2**: Remove max_keywords_per_neighbor constraint
5. **P3**: Consider adding should_evolve LLM decision
6. **P3**: Track evolution_history for debugging