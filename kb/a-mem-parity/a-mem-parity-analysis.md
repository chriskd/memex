---
title: A-Mem Parity Analysis
tags:
  - a-mem
  - analysis
  - parity
created: 2026-01-14T23:35:59.371670+00:00
updated: 2026-01-15T05:42:49.679903+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
semantic_links:
  - path: a-mem-parity/a-mem-evaluation-methodology.md
    score: 0.735
    reason: bidirectional
  - path: a-mem-parity/entry-metadata-schema.md
    score: 0.68
    reason: bidirectional
  - path: memex/chunking-system-design.md
    score: 0.632
    reason: bidirectional
---

# A-Mem Parity Analysis

This document compares our memex implementation against the A-Mem paper (NeurIPS 2025) to document feature parity, implementation differences, gaps, and our extensions.

## A-Mem Schema Reference

The A-Mem paper defines memory notes as:
```
m_i = {c_i, t_i, K_i, G_i, X_i, e_i, L_i}
```

| A-Mem Symbol | A-Mem Description | Our Field | Status |
|--------------|-------------------|-----------|--------|
| c_i | Original interaction content | `content` (markdown body) | Full |
| t_i | Timestamp | `created`, `updated` | Full |
| K_i | LLM-generated keywords | `keywords` field | Partial |
| G_i | LLM-generated tags | `tags` field | Partial |
| X_i | Contextual descriptions | `title` + `description` | Partial |
| e_i | Embedding vector | ChromaDB embeddings | Full |
| L_i | Linked memories | `semantic_links` field | Full |

## Feature Parity Table

| A-Mem Feature | Our Implementation | Parity Level | Notes |
|---------------|-------------------|--------------|-------|
| **Keyword extraction** | `keywords` field in frontmatter | Schema only | Field exists but not auto-populated by LLM |
| **Tag categorization** | `tags` field (required) | Manual | User-provided, not LLM-inferred |
| **Contextual descriptions** | `title` + optional `description` | Manual | User-provided |
| **Embedding computation** | `chroma_index.py` with MiniLM | Full | Includes keywords+tags in embedding text |
| **Embedding enrichment** | `_build_embedding_text()` | Full | Concatenates content+keywords+tags |
| **Similarity threshold** | `SEMANTIC_LINK_MIN_SCORE=0.6` | Full | Configurable in `config.py` |
| **Top-k neighbors** | `SEMANTIC_LINK_K=5` | Full | Configurable |
| **Bidirectional linking** | `create_bidirectional_semantic_links()` | Full | Auto-creates forward+backlinks |
| **Link reasons** | `reason` field: embedding_similarity, bidirectional, shared_tags | Extended | We track link provenance |
| **Graph-aware retrieval** | `--include-neighbors` flag | Full | BFS traversal up to 5 hops |
| **Memory evolution** | Neighbor update on add/edit | Partial | Backlinks added but no keyword/context evolution |
| **Aeiva scoring** | Not implemented | Gap | A-Mem uses importance-based decay |

## Implementation Differences

### 1. Embedding Strategy

**A-Mem**: Embeddings include content, keywords, and context descriptions in a structured format.

**Memex**: We use `_build_embedding_text()` which concatenates:
```python
content + "

Keywords: " + keywords + "
Tags: " + tags
```

This is semantically similar but less structured than A-Mem's approach.

### 2. Link Discovery Trigger

**A-Mem**: Links discovered during both creation and retrieval phases, with ongoing refinement.

**Memex**: Links discovered only on `add_entry()` and `update_entry()` when content changes. No retrieval-time link discovery.

### 3. Similarity Search

**A-Mem**: Uses cosine similarity with LLM-based relevance verification.

**Memex**: Uses cosine similarity only (ChromaDB HNSW with cosine distance). No LLM verification step.

### 4. Graph Traversal

**A-Mem**: Follows links during retrieval with aeiva-based importance weighting.

**Memex**: Simple BFS traversal with depth limit. All links treated equally.

## Gaps (A-Mem Has, We Lack)

### 1. LLM-Driven Metadata Generation

A-Mem uses an LLM to automatically generate:
- Keywords (K_i): Key concepts extracted from content
- Tags (G_i): Categorical classifications
- Context (X_i): Semantic understanding summaries

**Impact**: Our entries require manual tagging. Keywords field exists but is user-populated.

### 2. Memory Evolution / Neighbor Updates

A-Mem's key innovation: when a new memory is added, neighbors have their keywords and context updated to reflect the new connection.

**Impact**: Our backlinks are added but neighbor content/keywords are not evolved. The graph grows but individual nodes don't learn from connections.

### 3. Aeiva (Activation/Importance) Scoring

A-Mem maintains activation scores for memories, decaying over time and boosting on access. High-aeiva memories are prioritized in retrieval.

**Impact**: All our entries are equally weighted. No recency decay or access-based importance.

### 4. LLM-Based Link Verification

A-Mem verifies potential links with an LLM call to filter false positives from pure embedding similarity.

**Impact**: We may have weaker links that cosine similarity alone suggests are relevant.

### 5. Progressive Context Injection

A-Mem formats retrieved memories for optimal LLM consumption with structured context.

**Impact**: We return raw content; formatting for injection is left to consumers.

## Our Extensions Beyond A-Mem

### 1. Link Provenance (`reason` field)

We track why links exist:
- `embedding_similarity`: Discovered via vector search
- `bidirectional`: Backlink from another entry
- `shared_tags`: Future: discovered via tag overlap
- `manual`: User-specified

A-Mem doesn't explicitly track link provenance.

### 2. Scoped Knowledge Bases

We support multiple KB scopes:
- `@project/`: Project-specific knowledge
- `@user/`: Personal cross-project knowledge

A-Mem operates on a single memory store.

### 3. Breadcrumb Metadata

We capture creation context:
- `source_project`: Which project created this
- `git_branch`: Branch during creation
- `model`: LLM model used (if agent-created)
- `last_edited_by`: Agent vs human attribution

This enables provenance tracking that A-Mem lacks.

### 4. Hybrid Search (RRF)

We combine keyword search (Whoosh) with semantic search (ChromaDB) using Reciprocal Rank Fusion.

A-Mem is purely semantic.

### 5. Duplicate Detection

We detect potential duplicates before creating entries using `DUPLICATE_DETECTION_MIN_SCORE=0.75`.

A-Mem doesn't mention duplicate prevention.

## Configuration Reference

| Setting | Default | A-Mem Equivalent |
|---------|---------|------------------|
| `SEMANTIC_LINK_ENABLED` | `True` | Always on |
| `SEMANTIC_LINK_MIN_SCORE` | `0.6` | Paper uses 0.5-0.7 |
| `SEMANTIC_LINK_K` | `5` | Paper uses 5-10 |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Paper uses larger models |

## Recommendations for Full Parity

1. **Add LLM keyword extraction**: On entry creation, call LLM to populate `keywords` field automatically.

2. **Implement memory evolution**: When adding backlinks, also update neighbor keywords/context based on the new connection.

3. **Add aeiva scoring**: Track access patterns and implement importance decay.

4. **LLM link verification**: Add optional LLM call to verify embedding-based link candidates.

5. **Structured context injection**: Add output format for LLM-optimized context bundles.