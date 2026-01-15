---
title: A-Mem Parity Final Audit - 2026-01-15
tags: [a-mem, audit, parity, evolution]
keywords: [evolution, should_evolve, strengthen, update_neighbor, implementation]
created: 2026-01-15T02:00:00+00:00
---

# A-Mem Parity Final Audit - 2026-01-15

## Executive Summary

This audit compares the A-Mem reference implementation (`agentic_memory/memory_system.py`) against memex's implementation to identify parity gaps.

**Overall Status: ~85% Parity**

### Critical Findings

| Priority | Finding | Status |
|----------|---------|--------|
| HIGH | Strengthen action NOT integrated into workflow | Function exists but unused |
| MEDIUM | No consolidate_memories equivalent | Design choice (persistent indices) |
| LOW | evo_cnt/evo_threshold not implemented | Related to consolidation |

---

## Feature-by-Feature Comparison

### 1. MemoryNote Fields vs EntryMetadata

| A-Mem Field | A-Mem Location | Memex Equivalent | Memex Location | Status | Notes |
|-------------|----------------|------------------|----------------|--------|-------|
| `content` | MemoryNote:64 | Markdown body | File content | Match | Different format (file vs object) |
| `id` | MemoryNote:65 | File path | File system | Match | Path is natural ID |
| `keywords` | MemoryNote:68 | `EntryMetadata.keywords` | models.py:81 | Match | LLM-extracted key concepts |
| `links` | MemoryNote:69 | `EntryMetadata.semantic_links` | models.py:82 | Match | Computed relationships |
| `retrieval_count` | MemoryNote:80 | `ViewStats.total_views` | views_tracker.py:160 | Match | Persistent tracking |
| `timestamp` | MemoryNote:76 | `EntryMetadata.created` | models.py:66 | Match | ISO format datetime |
| `last_accessed` | MemoryNote:77 | `ViewStats.last_viewed` | views_tracker.py:161 | Match | Updated on each view |
| `context` | MemoryNote:70 | `EntryMetadata.description` | models.py:64 | Match | One-line semantic summary |
| `evolution_history` | MemoryNote:81 | `EntryMetadata.evolution_history` | models.py:83 | Match | List of EvolutionRecord |
| `category` | MemoryNote:71 | Directory path | File system | Match | Directory structure |
| `tags` | MemoryNote:72 | `EntryMetadata.tags` | models.py:65 | Match | Classification tags |

**Status: FULL PARITY on data model**

---

### 2. Evolution System Prompt

| A-Mem Field | A-Mem Location | Memex Equivalent | Memex Location | Status | Notes |
|-------------|----------------|------------------|----------------|--------|-------|
| `_evolution_system_prompt` | memory_system.py:127-157 | `analyze_evolution()` prompt | llm.py:414-452 | Match | Different wording, same semantics |
| `should_evolve` decision | Line 674 | `EvolutionDecision.should_evolve` | models.py:46 | Match | LLM explicit decision |
| `actions: ["strengthen", "update_neighbor"]` | Lines 677-716 | `actions` field | models.py:47 | Partial | See below |
| `suggested_connections` | Line 680 | `EvolutionDecision.suggested_connections` | models.py:49 | Match | Neighbor paths to link |
| `tags_to_update` (new entry) | Line 683 | `StrengthenResult.new_keywords` | llm.py:716 | Missing Integration | Function exists but NOT called |
| `new_context_neighborhood` | Line 696 | `NeighborUpdate.new_context` | models.py:29 | Match | Per-neighbor context |
| `new_tags_neighborhood` | Line 695 | `NeighborUpdate.new_keywords` | models.py:28 | Match | REPLACES existing |

**Status: 80% PARITY - strengthen action incomplete**

---

### 3. Process Memory (Evolution Logic)

| A-Mem Feature | A-Mem Location | Memex Equivalent | Memex Location | Status | Notes |
|---------------|----------------|------------------|----------------|--------|-------|
| Single LLM call for both actions | process_memory():590-727 | `analyze_evolution()` | llm.py:369-531 | Match | Unified decision |
| Check `should_evolve` first | Line 674 | core.py:808-811 | process_evolution_items() | Match | Respects LLM decision |
| Strengthen: update NEW entry links | Line 682 | analyze_for_strengthen() | llm.py:722-847 | Missing Integration | Function exists, NOT called |
| Strengthen: update NEW entry tags | Line 683 | analyze_for_strengthen() | llm.py:716 | Missing Integration | Function exists, NOT called |
| Update_neighbor: tags REPLACE | Line 695 | core.py:836 | updated_keywords = update.new_keywords | Match | Replace semantics |
| Update_neighbor: context update | Line 697 | core.py:829-831 | new_description | Match | Updates description |
| Increment evo_cnt | Line 261 | N/A | N/A | Missing | No equivalent counter |
| Trigger consolidation | Line 262-263 | N/A | N/A | Design Diff | See consolidation section |

**Status: ~80% PARITY - strengthen flow incomplete**

---

### 4. analyze_content() - Keyword Extraction

| A-Mem Feature | A-Mem Location | Memex Equivalent | Memex Location | Status | Notes |
|---------------|----------------|------------------|----------------|--------|-------|
| Extract keywords from content | analyze_content():159-231 | `extract_keywords_llm()` | llm.py:605-700 | Match | LLM-based extraction |
| Extract context (semantic summary) | Line 189 | Not in keyword extraction | N/A | Different | Description set separately |
| Extract tags | Line 195 | Tags provided by user | add_entry() | Different | User-provided, not extracted |
| JSON schema validation | Lines 205-227 | `_extract_first_json_object()` | llm.py:534-588 | Match | Robust JSON parsing |

**Status: PARTIAL PARITY - tags not auto-extracted**

---

### 5. add_note() - Add Entry Flow

| A-Mem Feature | A-Mem Location | Memex Equivalent | Memex Location | Status | Notes |
|---------------|----------------|------------------|----------------|--------|-------|
| Create memory object | add_note():233-264 | `add_entry()` | core.py:1335-1545 | Match | Creates entry file |
| Call process_memory() sync | Line 241 | `_queue_evolution()` async | core.py:1496-1501 | Better | Non-blocking evolution |
| Update retriever | Line 258 | `searcher.index_chunks()` | core.py:1459-1468 | Match | Immediate indexing |
| Return ID | Line 264 | Returns dict with path | core.py returns dict | Match | Path as ID |

**Status: FULL PARITY (improved with async)**

---

### 6. consolidate_memories() - Index Rebuild

| A-Mem Feature | A-Mem Location | Memex Equivalent | Memex Location | Status | Notes |
|---------------|----------------|------------------|----------------|--------|-------|
| Reset ChromaDB collection | consolidate_memories():266-286 | N/A | N/A | Missing | Design difference |
| Trigger after evo_threshold | Lines 261-263 | N/A | N/A | Missing | No threshold counter |
| Re-add all memories | Lines 272-286 | `mx reindex` | CLI command | Alternative | Manual reindex |

**Status: DESIGN DIFFERENCE - memex uses persistent indices**

A-Mem periodically rebuilds ChromaDB after N evolutions. Memex maintains persistent indices and uses `mx reindex` for manual rebuilding. This is a conscious design choice, not a gap.

---

### 7. find_related_memories() / Search

| A-Mem Feature | A-Mem Location | Memex Equivalent | Memex Location | Status | Notes |
|---------------|----------------|------------------|----------------|--------|-------|
| ChromaDB vector search | find_related_memories():288-313 | `searcher.search()` | Chroma backend | Match | Same technology |
| Return (text, indices) tuple | Line 310 | Returns SearchResult list | models.py:96 | Better | Structured results |
| Include linked neighbors | search_agentic():509-588 | `--include-neighbors` flag | cli.py:968 | Match | Graph-aware search |
| Add neighbor metadata | Lines 572-583 | expand_with_neighbors() | core.py:1253-1326 | Match | Full neighbor data |

**Status: FULL PARITY**

---

### 8. Evolution History Tracking

| A-Mem Feature | A-Mem Location | Memex Equivalent | Memex Location | Status | Notes |
|---------------|----------------|------------------|----------------|--------|-------|
| Track evolution_history list | MemoryNote:81 | `EntryMetadata.evolution_history` | models.py:83 | Match | List of records |
| Record trigger entry | Line 715 | `EvolutionRecord.trigger_entry` | models.py:13 | Match | Path of triggering entry |
| Record keyword changes | Line 711 | `EvolutionRecord.previous_keywords`, `new_keywords` | models.py:14-15 | Match | Before/after |
| Record context changes | Line 713-714 | `EvolutionRecord.previous_description`, `new_description` | models.py:16-17 | Match | Before/after |
| Timestamp evolution | Line 715 | `EvolutionRecord.timestamp` | models.py:12 | Match | When it occurred |

**Status: FULL PARITY**

---

## Gaps Requiring Action

### HIGH Priority: Strengthen Action Not Integrated

**Problem:** `analyze_for_strengthen()` exists in llm.py:722-847 but is NEVER called.

**Config exists:** `strengthen_on_add` in config.py:555-559

**Impact:** When new entries are added and linked to neighbors, the new entry's keywords are NOT refined based on discovered relationships.

**A-Mem Behavior:**
```python
if action == "strengthen":
    note.links.extend(suggested_connections)
    note.tags = tags_to_update  # Update NEW entry
```

**Memex Current:** Only updates neighbors, never the new entry itself.

**Fix Required:** In `add_entry()` or `_queue_evolution()`, call `analyze_for_strengthen()` when `config.strengthen_on_add` is True and apply the result to update the new entry's keywords/links.

---

### MEDIUM Priority: No Automatic Tag Extraction

**Problem:** A-Mem's `analyze_content()` extracts tags from content. Memex requires users to provide tags.

**Impact:** Users must manually specify tags; no semantic tag inference.

**Note:** This may be intentional UX design. Tags in memex serve as user-defined categories, while A-Mem uses them as additional semantic metadata.

---

### LOW Priority: No consolidate_memories Equivalent

**Problem:** A-Mem periodically rebuilds ChromaDB after `evo_threshold` evolutions.

**Memex Alternative:** `mx reindex` for manual rebuilding.

**Impact:** None in practice - memex indices are persistent and accurate.

---

## Worktree Status

Checked all worktrees for uncommitted work:

| Worktree | Status |
|----------|--------|
| `.worktrees/amem-strict/` | Modified: remaining-a-mem-implementation-gap.md |
| `.worktrees/ingest-feature/` | Modified: remaining-a-mem-implementation-gap.md |
| `.worktrees/llm-provider-unification/` | Clean (submodule refs only) |

### Unmerged Branches

All significant branches have been merged to main:
- `evolution-history-tracking` - Merged
- `should-evolve-feature` - Merged
- `strengthen-action` - Already in main (branch not deleted)
- `llm-provider-unification` - Already in main (branch not deleted)

**Note:** Branches show as "unmerged" but `git log main..branch` shows no unique commits. Safe to delete.

---

## Recommendations

1. **Integrate strengthen action** - Add call to `analyze_for_strengthen()` in add_entry flow when neighbors are found and config enables it.

2. **Clean up stale branches** - Delete `strengthen-action`, `should-evolve-feature`, `llm-provider-unification`, `evolution-history-tracking` as they're fully merged.

3. **Update KB documentation** - Mark remaining-a-mem-implementation-gap.md as COMPLETED or archive it.

4. **Consider tag extraction** - Optionally add automatic tag suggestion during add_entry (already exists as `suggested_tags`).

---

## Appendix: A-Mem Reference Locations

Key sections in `/tmp/amem-ref/agentic_memory/memory_system.py`:

- **MemoryNote class**: Lines 24-81
- **_evolution_system_prompt**: Lines 127-157
- **analyze_content()**: Lines 159-231
- **add_note()**: Lines 233-264
- **consolidate_memories()**: Lines 266-286
- **find_related_memories()**: Lines 288-313
- **search_agentic()**: Lines 509-588
- **process_memory()**: Lines 590-727
