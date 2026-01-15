---
title: a-mem-init Command Specification
tags:
  - a-mem
  - cli
  - specification
  - feature
created: 2026-01-15T02:13:58.692765+00:00
updated: 2026-01-15T02:55:09.466313+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
git_branch: main
last_edited_by: chris
keywords:
  - a-mem-init
  - bootstrap
  - semantic-linking
  - chronological-processing
  - keyword-extraction
  - graph-initialization
semantic_links:
  - path: a-mem-parity/semantic-linking.md
    score: 0.67
    reason: embedding_similarity
  - path: a-mem-parity/entry-metadata-schema.md
    score: 0.617
    reason: embedding_similarity
---

# a-mem-init Command Specification
Tags: a-mem, cli, specification, feature
------------------------------------------------------------
# a-mem-init Command Specification

Initialize A-Mem structures (semantic links + evolution queue) for an existing knowledge base.

## Problem Statement

When a KB has existing entries that predate A-Mem features (semantic linking, evolution), there is no way to retroactively:
1. Create semantic links between related entries
2. Queue evolution work so entries can learn from each other
3. Fill in missing keywords (required for embedding enrichment)

The A-Mem paper assumes incremental addition but does not address bootstrapping.

## Command Design

```bash
mx a-mem-init [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--missing-keywords` | `llm\|error\|skip` | (see below) | How to handle entries without keywords |
| `--scope` | `project\|user` | both | Limit to specific KB scope |
| `--dry-run` | flag | false | Show what would be done without executing |
| `--limit` | int | none | Process up to N entries (for testing) |
| `--json` | flag | false | Output as JSON |

### Missing Keywords Behavior

Default depends on `amem_strict` config:
- If `amem_strict: true` â default is `error`
- If `amem_strict: false` â default is `skip`

| Mode | Behavior |
|------|----------|
| `llm` | Call LLM (from kbconfig `memory_evolution.model`) to extract keywords |
| `error` | Stop and report entries missing keywords, do not proceed |
| `skip` | Skip entries without keywords, continue with others |

## Algorithm

### Phase 1: Inventory & Validation

```
1. List all entries in scope, sorted by `created` timestamp (oldest first)
2. For each entry:
   a. Check if keywords field exists and is non-empty
   b. If missing and mode=error: collect path, continue checking all
   c. If missing and mode=skip: mark as skipped
   d. If missing and mode=llm: queue for keyword extraction
3. If mode=error and any missing: print list and exit with error
```

### Phase 2: Keyword Extraction (if mode=llm)

```
1. For each entry needing keywords:
   a. Read content
   b. Call LLM to extract 3-6 keywords
   c. Update entry frontmatter with keywords
   d. Re-index entry (embeddings now include keywords)
2. Report: N entries updated with keywords
```

### Phase 3: Semantic Linking (Chronological)

**Critical**: Process in chronological order to simulate incremental addition.

```
1. For each entry (oldest to newest):
   a. Call create_bidirectional_semantic_links()
   b. This searches for similar OLDER entries only (by created date)
   c. Creates forward links on current entry
   d. Creates backlinks on neighbor entries
   e. Collects neighbors for evolution queue
2. Report: N entries linked, M total links created
```

**Why chronological?** 
- Simulates how A-Mem would have worked if entries were added one-by-one
- Older entries get backlinks from newer ones (natural growth pattern)
- Evolution queue reflects realistic "new entry impacts old neighbors" relationship

### Phase 4: Evolution Queue Population

```
1. For each linking operation, queue (new_entry, neighbor, score) tuples
2. Do NOT run evolution automatically (user runs `mx evolve` separately)
3. Report: N items queued for evolution
```

## Output Examples

### Dry Run
```
$ mx a-mem-init --dry-run

A-Mem Init (dry run)
ââââââââââââââââââââ

Entries to process: 42
  - With keywords: 38
  - Missing keywords: 4 (will skip)

Processing order (oldest first):
  1. 2024-03-15  guides/getting-started.md
  2. 2024-03-16  guides/configuration.md
  ...
  42. 2026-01-14  a-mem-parity/a-mem-init.md

Estimated operations:
  - Semantic link searches: 42
  - Potential links: ~126 (avg 3 per entry)
  - Evolution queue items: ~126

Run without --dry-run to execute.
```

### Error Mode (missing keywords)
```
$ mx a-mem-init --missing-keywords=error

Error: 4 entries are missing keywords

  guides/old-note.md
  reference/legacy-api.md
  troubleshooting/fix-xyz.md
  tools/script-docs.md

Add keywords to these entries or use --missing-keywords=skip to proceed without them.
```

### Success
```
$ mx a-mem-init

A-Mem Init
ââââââââââ

Phase 1: Inventory
  Entries found: 42
  With keywords: 42
  Skipped: 0

Phase 2: Keyword Extraction
  (skipped - all entries have keywords)

Phase 3: Semantic Linking
  Processed: 42 entries (chronological order)
  Links created: 127 bidirectional pairs
  Entries with links: 39

Phase 4: Evolution Queue
  Items queued: 127

â A-Mem initialization complete

Next step: Run `mx evolve` to process the evolution queue.
```

## Implementation Notes

### Chronological Linking Constraint

When calling `create_bidirectional_semantic_links()` for entry E:
- Only consider entries with `created < E.created` as potential neighbors
- This requires modifying the search to filter by date, OR
- Pre-filter the candidate pool before similarity search

Option A (filter search results):
```python
neighbors = search_similar(entry_content, k=k*2)  # Get extra
neighbors = [n for n in neighbors if n.created < entry.created][:k]
```

Option B (staged processing):
```python
# Index entries one at a time in chronological order
for entry in sorted_entries:
    index_entry(entry)  # Now in search pool
    link_to_existing(entry)  # Only finds older entries
```

Option B is cleaner but slower. Option A is pragmatic.

### LLM Keyword Extraction Prompt

```
Extract 3-6 keywords from this content. Keywords should be:
- Domain-specific concepts (not generic words)
- Key entities, technologies, or patterns mentioned
- Related concepts that aid discoverability

Content:
{content}

Return JSON: {"keywords": ["keyword1", "keyword2", ...]}
```

### Idempotency

Running `a-mem-init` multiple times should be safe:
- Semantic links: Skip entries that already have links (or re-run and dedupe)
- Evolution queue: May add duplicate items (queue processing handles this)
- Keywords: Skip entries that already have keywords

### Performance Considerations

- Large KBs (1000+ entries): Use batching, progress bar
- LLM calls: Rate limit, estimate cost before proceeding
- Indexing: Consider bulk reindex after all updates

## Success Criteria

1. All entries (with keywords) have semantic links to related entries
2. Links are bidirectional (forward + backlink)
3. Evolution queue is populated for later processing
4. Entries without keywords are handled according to mode
5. Command is idempotent (safe to re-run)

## Implementation Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Inventory & Validation | ✅ Complete | `amem_init_inventory()` in core.py, CLI options, 20 tests |
| Phase 2: Keyword Extraction | ✅ Complete | `extract_keywords_llm()` in llm.py, `amem_init_extract_keywords()` in core.py, 16 new tests |
| Phase 3: Semantic Linking | ✅ Complete | `amem_init_link_entries()` in core.py, chronological processing, 16 new tests |
| Phase 4: Evolution Queue | ✅ Complete | Integrated with Phase 3, uses `queue_evolution()` |

### Phase 1 Implementation Details

- **Core function**: `amem_init_inventory()` in `src/memex/core.py`
- **Models**: `InitInventoryEntry`, `InitInventoryResult` in `src/memex/models.py`
- **CLI**: `mx a-mem-init` with `--missing-keywords`, `--scope`, `--dry-run`, `--limit`, `--json`
- **Tests**: `tests/test_amem_init.py` (20 tests)
- **Commit**: `1cbe6d8` (2026-01-14)

### Phase 2 Implementation Details

- **LLM function**: `extract_keywords_llm()` in `src/memex/llm.py` - extracts 3-6 keywords from content
- **Core function**: `amem_init_extract_keywords()` in `src/memex/core.py` - processes entries needing LLM
- **Models**: `KeywordExtractionEntry`, `KeywordExtractionPhaseResult` in `src/memex/models.py`
- **CLI integration**: Phase 2 runs automatically when `--missing-keywords=llm` and not `--dry-run`
- **Tests**: 16 new tests in `tests/test_amem_init.py` (36 total)
- **Features**:
  - Uses model from `.kbconfig` → `memory_evolution.model`
  - Updates entry frontmatter with extracted keywords
  - Triggers re-indexing after keyword addition
  - Handles errors gracefully, continues processing remaining entries
  - JSON output includes `phase2` object with detailed results

### Phase 3 & 4 Implementation Details

- **Core function**: `amem_init_link_entries()` in `src/memex/core.py`
- **Models**: `LinkingPhaseEntry`, `LinkingPhaseResult` in `src/memex/models.py`
- **CLI integration**: Phase 3 runs automatically after Phase 1/2 when not `--dry-run`
- **Tests**: 16 new tests in `tests/test_amem_init.py` (52 total)
- **Features**:
  - Processes entries chronologically (oldest first)
  - Only links to entries created BEFORE current entry (Option A from spec)
  - Creates bidirectional links (forward + backlinks)
  - Queues evolution items via `queue_evolution()` (Phase 4 integration)
  - Idempotent: re-running doesn't create duplicate links
  - Skips entries without keywords
  - JSON output includes `phase3` object with detailed results

## Related

- [[a-mem-parity/semantic-linking.md]] - How semantic linking works
- [[a-mem-parity/memory-evolution-queue-architecture.md]] - Evolution queue design
- [[a-mem-parity/a-mem-strict-mode.md]] - Strict mode for keyword enforcement
