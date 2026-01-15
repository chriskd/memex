---
title: A-Mem Parity Audit - Paranoid Mode (2026-01-15)
tags:
  - a-mem
  - audit
  - parity
  - evolution
  - critical
created: 2026-01-15T05:30:00+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
keywords:
  - evolution
  - _get_openai_client
  - analyze_evolution
  - analyze_for_strengthen
  - NameError
  - broken
---

# A-Mem Parity Audit - Paranoid Mode (2026-01-15)

## Executive Summary

This paranoid-mode audit performs a thorough top-down comparison of A-Mem reference (`/tmp/amem-ref/agentic_memory/memory_system.py`) against memex implementation.

**Overall Status: ~75% FUNCTIONAL PARITY**

### CRITICAL FINDING

| Priority | Finding | Status | Impact |
|----------|---------|--------|--------|
| **CRITICAL** | `_get_openai_client()` undefined | BROKEN | Evolution completely non-functional |
| HIGH | Strengthen action calls broken function | BROKEN | Always silently fails |
| MEDIUM | consolidate_memories not implemented | Design choice | N/A |
| LOW | evo_cnt/evo_threshold not implemented | Related to above | N/A |

---

## CRITICAL BUG: `_get_openai_client()` Undefined

### Evidence

```bash
$ uv run python -c "
from memex.llm import analyze_evolution, NeighborInfo
import asyncio
async def test():
    neighbors = [NeighborInfo(path='test.md', title='Test', content='c', keywords=['k'], score=0.8)]
    await analyze_evolution('title', 'content', ['kw'], neighbors, 'test-model')
asyncio.run(test())
"
# Result:
NameError: name '_get_openai_client' is not defined
```

### Affected Functions

| Function | Location | Status |
|----------|----------|--------|
| `analyze_evolution()` | llm.py:369 | BROKEN - calls `_get_openai_client()` at line 399 |
| `analyze_for_strengthen()` | llm.py:722 | BROKEN - calls `_get_openai_client()` at line 755 |

### Working Functions (use `_get_client()`)

| Function | Location | Status |
|----------|----------|--------|
| `evolve_single_neighbor()` | llm.py:65 | WORKING |
| `evolve_neighbors_batched()` | llm.py:206 | WORKING |
| `extract_keywords_llm()` | llm.py:605 | WORKING |

### Root Cause

The LLM provider unification (commit `e1efb74`) merged support for Anthropic + OpenRouter via `_get_client()`, but:
1. `_get_openai_client()` was removed/renamed
2. `analyze_evolution()` and `analyze_for_strengthen()` were NOT updated to use `_get_client()`

### Impact

1. **`mx evolve` command**: Completely broken. `process_evolution_items()` in core.py calls `analyze_evolution()`, which raises `NameError`.

2. **Strengthen on add**: Completely broken. `add_entry()` calls `analyze_for_strengthen()` when `strengthen_on_add: true`, but silently fails due to exception handling.

### Fix Required

Replace in `llm.py`:
```python
# Line 399 (analyze_evolution):
client = _get_openai_client()  # BROKEN
# Should be:
client, provider = _get_client()

# Line 755 (analyze_for_strengthen):
client = _get_openai_client()  # BROKEN
# Should be:
client, provider = _get_client()
```

Then update both functions to use provider-appropriate API calls (like `evolve_single_neighbor()` does).

---

## Feature-by-Feature Comparison

### 1. MemoryNote Fields vs EntryMetadata

| A-Mem Field | A-Mem Location | Memex Equivalent | Memex Location | Status |
|-------------|----------------|------------------|----------------|--------|
| `content` | MemoryNote:64 | Markdown body | File content | ✅ Match |
| `id` | MemoryNote:65 | File path | File system | ✅ Match |
| `keywords` | MemoryNote:68 | `EntryMetadata.keywords` | models.py:81 | ✅ Match |
| `links` | MemoryNote:69 | `EntryMetadata.semantic_links` | models.py:82 | ✅ Match |
| `retrieval_count` | MemoryNote:80 | `ViewStats.total_views` | views_tracker.py:160 | ✅ Match |
| `timestamp` | MemoryNote:76 | `EntryMetadata.created` | models.py:66 | ✅ Match |
| `last_accessed` | MemoryNote:77 | `ViewStats.last_viewed` | views_tracker.py:161 | ✅ Match |
| `context` | MemoryNote:70 | `EntryMetadata.description` | models.py:64 | ✅ Match |
| `evolution_history` | MemoryNote:81 | `EntryMetadata.evolution_history` | models.py:83 | ✅ Match |
| `category` | MemoryNote:71 | Directory path | File system | ✅ Match |
| `tags` | MemoryNote:72 | `EntryMetadata.tags` | models.py:65 | ✅ Match |

**Data Model Status: FULL PARITY** ✅

---

### 2. Evolution System

| A-Mem Feature | A-Mem Location | Memex Equivalent | Memex Location | Status |
|---------------|----------------|------------------|----------------|--------|
| `_evolution_system_prompt` | memory_system.py:127-157 | Prompt in `analyze_evolution()` | llm.py:414-452 | ✅ Match |
| LLM `should_evolve` decision | Line 674 | `EvolutionDecision.should_evolve` | models.py:46 | ✅ Match |
| Actions: `strengthen` | Line 679 | `StrengthenResult` | llm.py:703-719 | ❌ BROKEN |
| Actions: `update_neighbor` | Line 684 | `NeighborUpdate` | models.py:20-30 | ❌ BROKEN |
| `suggested_connections` | Line 680 | `suggested_connections` field | models.py:49 | ❌ BROKEN |
| `new_context_neighborhood` | Line 696 | `NeighborUpdate.new_context` | models.py:29 | ❌ BROKEN |
| `new_tags_neighborhood` | Line 695 | `NeighborUpdate.new_keywords` | models.py:28 | ❌ BROKEN |

**Evolution Status: DESIGNED BUT NON-FUNCTIONAL** ❌

The data structures exist, the prompts exist, but `analyze_evolution()` raises `NameError` at runtime.

---

### 3. add_note() / add_entry() Flow

| A-Mem Feature | A-Mem Location | Memex Equivalent | Memex Location | Status |
|---------------|----------------|------------------|----------------|--------|
| Create memory object | add_note():233-264 | `add_entry()` | core.py:1335-1545 | ✅ Match |
| Call process_memory() | Line 241 | `_queue_evolution()` | core.py:1538-1544 | ✅ Better (async) |
| Strengthen on add | Line 682 | strengthen integration | core.py:1546-1613 | ❌ BROKEN |
| Update retriever | Line 258 | `searcher.index_chunks()` | core.py:1503-1510 | ✅ Match |

**Add Entry Status: MOSTLY WORKING, strengthen broken**

---

### 4. analyze_content() - Keyword Extraction

| A-Mem Feature | A-Mem Location | Memex Equivalent | Memex Location | Status |
|---------------|----------------|------------------|----------------|--------|
| Extract keywords | analyze_content():176-186 | `extract_keywords_llm()` | llm.py:605-700 | ✅ Working |
| Extract context | Line 189 | Not in keyword extraction | N/A | ⚠️ Different |
| Extract tags | Line 195 | Tags provided by user | add_entry() | ⚠️ Different |

**Keyword Extraction Status: WORKING** ✅

---

### 5. Search / Retrieval

| A-Mem Feature | A-Mem Location | Memex Equivalent | Memex Location | Status |
|---------------|----------------|------------------|----------------|--------|
| ChromaDB vector search | find_related_memories():288-313 | `searcher.search()` | indexer.py | ✅ Match |
| Return neighbors | search_agentic():509-588 | `--include-neighbors` | cli.py | ✅ Match |
| Linked neighbor data | Lines 572-583 | `expand_with_neighbors()` | core.py:1253-1326 | ✅ Match |

**Search Status: FULL PARITY** ✅

---

### 6. Evolution History Tracking

| A-Mem Feature | A-Mem Location | Memex Equivalent | Memex Location | Status |
|---------------|----------------|------------------|----------------|--------|
| Track evolution_history | MemoryNote:81 | `EntryMetadata.evolution_history` | models.py:83 | ✅ Match |
| Record trigger_entry | Line 715 | `EvolutionRecord.trigger_entry` | models.py:13 | ✅ Match |
| Record keyword changes | Line 711 | `previous_keywords`, `new_keywords` | models.py:14-15 | ✅ Match |
| Record context changes | Lines 713-714 | `previous_description`, `new_description` | models.py:16-17 | ✅ Match |

**Evolution History Status: FULL PARITY (data model)** ✅
**Note:** History tracking works but evolution itself is broken, so history is never populated.

---

### 7. consolidate_memories() - Index Rebuild

| A-Mem Feature | A-Mem Location | Memex Equivalent | Memex Location | Status |
|---------------|----------------|------------------|----------------|--------|
| Reset ChromaDB | consolidate_memories():266-286 | N/A | N/A | ⚠️ Design diff |
| evo_threshold trigger | Lines 261-263 | N/A | N/A | ⚠️ Design diff |
| Re-add all memories | Lines 272-286 | `mx reindex` | CLI | ✅ Alternative |

**Consolidation Status: DESIGN DIFFERENCE (acceptable)**

Memex uses persistent indices with manual `mx reindex`. A-Mem uses ephemeral ChromaDB with periodic rebuilds. Both approaches are valid.

---

## Worktree & Branch Status

### Worktrees

| Worktree | Status |
|----------|--------|
| `.worktrees/amem-strict/` | Empty (no changes) |
| `.worktrees/ingest-feature/` | Empty (no changes) |

### Unmerged Branches

| Branch | Last Commit | Notes |
|--------|-------------|-------|
| `backup-before-filter-*` | bff1cac | Backup branch, safe to delete |
| `beads-sync` | bb06cff | Auto-sync branch |
| `feature/memex-rename` | 23c77c7 | Old rename branch |
| `k3o5-auto-semantic-links` | 606cff9 | Old feature branch |
| `pr-2`, `pr-3`, `pr-4` | Various | PR branches |
| `responsive-mobile-design` | a90332f | Publisher feature |
| `w9nc-include-neighbors` | e465fcb | Graph-aware search (merged?) |

**No uncommitted work in worktrees.** ✅

---

## Summary of Issues

### MUST FIX (Blocking)

1. **`_get_openai_client()` undefined in llm.py**
   - Location: Lines 399, 755
   - Fix: Replace with `_get_client()` and update API call patterns
   - Impact: Evolution completely broken

### SHOULD FIX (Non-blocking)

1. **Test coverage for broken functions**
   - `analyze_evolution()` tests may be passing due to mocking
   - Need integration test that actually calls LLM client

### ACCEPTABLE DIFFERENCES

1. **consolidate_memories** - Design choice, memex uses persistent indices
2. **Auto-tag extraction** - User provides tags, not auto-extracted
3. **evo_cnt/evo_threshold** - Related to consolidation design

---

## Recommendations

1. **IMMEDIATE**: Fix `_get_openai_client()` references in llm.py
2. **HIGH**: Add integration test that verifies LLM client initialization
3. **MEDIUM**: Clean up stale branches
4. **LOW**: Consider deprecating `analyze_evolution()` in favor of `evolve_neighbors_batched()` which works

---

## Appendix: Verification Commands

```bash
# Verify broken function
uv run python -c "from memex.llm import analyze_evolution, NeighborInfo; import asyncio
neighbors = [NeighborInfo(path='test.md', title='Test', content='c', keywords=['k'], score=0.8)]
asyncio.run(analyze_evolution('t', 'c', ['k'], neighbors, 'model'))"
# Expected: NameError: name '_get_openai_client' is not defined

# Verify working function
uv run python -c "from memex.llm import evolve_single_neighbor; print('Import OK')"
# Expected: Import OK
```
