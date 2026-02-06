---
title: Chunking System Design
tags:
  - memex
  - architecture
  - chunking
created: 2026-01-15T05:42:42.968730+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
git_branch: main
last_edited_by: chris
---

# Chunking System for Memex

## Goal
Add configurable chunking that stores chunks **only in ChromaDB** while keeping markdown files whole. This enables:
1. **Precise snippet retrieval** for semantic search
2. **Finer-grained relevance** for long documents
3. **Evaluation of chunking strategies** via retrieval benchmarks

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Chunk storage | ChromaDB only | No file clutter, markdown stays human-readable |
| Default strategy | `headers` | Backward compatible; easy opt-in to `paragraph` |
| Priority strategy | `sentences` | Best for fine-grained retrieval |
| Search default | Dedupe by file | Backward compatible, `--show-chunks` for granular |
| Eval suite | Specs now, impl Phase 2 | Ship chunking first, validate after |

## Configuration

```yaml
# .kbconfig
chunking:
  enabled: true
  strategy: paragraph    # headers, paragraph, semantic, sentences
  max_chunk_tokens: 256  # For semantic strategy
  overlap_tokens: 32     # Context continuity
  min_chunk_tokens: 20   # Avoid tiny chunks
```

## Implementation Phases

### Phase 1: Configuration (config.py)
- Add `ChunkingConfig` dataclass
- Add `get_chunking_config()` loader
- Update .kbconfig template in cli.py

### Phase 2: Chunking Strategies (parser/)
- Create `src/memex/parser/chunking.py` module
- Implement strategies:
  - `chunk_by_headers()` - refactor existing `_chunk_by_h2()`
  - `chunk_by_paragraph()` - split on double newlines
  - `chunk_by_semantic()` - sentence boundaries + token limits
  - `chunk_by_sentences()` - individual sentences
- Add sentence splitting utility with offset tracking

### Phase 3: Index Schema Updates (indexer/)
- **ChromaDB ID format**: `path#chunk_{idx}` or `path#{section}#chunk_{idx}`
- **New metadata fields**: `chunk_idx`, `parent_section`, `chunk_strategy`, `start_offset`, `end_offset`
- **Update delete logic**: Query by path metadata, not ID pattern

### Phase 4: Models Update (models.py)
- Extend `DocumentChunk` with:
  - `chunk_idx: int`
  - `parent_section: str | None`
  - `chunk_strategy: str`
  - `start_offset: int`
  - `end_offset: int`

### Phase 5: Search & CLI Updates
- Add `--show-chunks` flag to search command
- Update SearchResult with chunk metadata
- JSON output includes full chunk info

### Phase 6: Migration & Reindex
- Store `chunking_strategy` in collection metadata
- Detect strategy mismatch, warn user
- Add `mx reindex --force-rechunk` command

## Critical Files

| File | Changes |
|------|---------|
| `src/memex/config.py` | Add ChunkingConfig dataclass |
| `src/memex/parser/chunking.py` | NEW - chunking strategies |
| `src/memex/parser/markdown.py` | Refactor to use chunking module |
| `src/memex/indexer/chroma_index.py` | New ID format, metadata fields |
| `src/memex/indexer/whoosh_index.py` | Match schema changes |
| `src/memex/models.py` | Extend DocumentChunk |
| `src/memex/cli.py` | Add --show-chunks, config template |
| `tests/test_chunking.py` | NEW - chunking tests |

## Semantic Chunking Algorithm

```
1. Split content into sentences with character offsets
2. Accumulate sentences until max_tokens reached
3. On overflow: create chunk, start new with overlap
4. Handle edge cases: code blocks, long sentences
```

## Verification

1. **Unit tests**: Each strategy produces expected chunks
2. **Integration**: `mx reindex --force-rechunk` with each strategy
3. **Search**: `mx search "query" --show-chunks` returns chunk-level results
4. **Migration**: Strategy change detected, warning shown
