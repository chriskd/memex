---
title: Remaining A-Mem Implementation Gap
tags: [a-mem, evolution, parity, specification]
keywords: [should_evolve, unified-prompt, evolution-decision]
created: 2026-01-15T00:15:00+00:00
---

# Remaining A-Mem Implementation Gap

## Executive Summary

**ONE thing remains to achieve full A-Mem parity: the unified evolution prompt with `should_evolve` decision.**

We currently use separate LLM calls with no `should_evolve` decision. A-Mem uses ONE call that decides whether to evolve at all.

---

## What A-Mem Does (Reference: memory_system.py lines 127-157, 620-717)

### Single Unified LLM Call

A-Mem makes ONE LLM call that returns:

```json
{
  "should_evolve": true,
  "actions": ["strengthen", "update_neighbor"],
  "suggested_connections": ["neighbor_id_1", "neighbor_id_2"],
  "tags_to_update": ["tag1", "tag2"],
  "new_context_neighborhood": ["context for neighbor 1", "context for neighbor 2"],
  "new_tags_neighborhood": [["tags", "for", "neighbor1"], ["tags", "for", "neighbor2"]]
}
```

### The Prompt (exact text from A-Mem)

```
You are an AI memory evolution agent responsible for managing and evolving a knowledge base.
Analyze the new memory note according to keywords and context, also with their several nearest neighbors memory.
Make decisions about its evolution.

The new memory context:
{context}
content: {content}
keywords: {keywords}

The nearest neighbors memories:
{nearest_neighbors_memories}

Based on this information, determine:
1. Should this memory be evolved? Consider its relationships with other memories.
2. What specific actions should be taken (strengthen, update_neighbor)?
   2.1 If choose to strengthen the connection, which memory should it be connected to? Can you give the updated tags of this memory?
   2.2 If choose to update_neighbor, you can update the context and tags of these memories based on the understanding of these memories.

The number of neighbors is {neighbor_number}.
Return your decision in JSON format with the following structure:
{
    "should_evolve": True or False,
    "actions": ["strengthen", "update_neighbor"],
    "suggested_connections": ["neighbor_memory_ids"],
    "tags_to_update": ["tag_1"..."tag_n"],
    "new_context_neighborhood": ["new context",...,"new context"],
    "new_tags_neighborhood": [["tag_1",...,"tag_n"],...["tag_1",...,"tag_n"]]
}
```

### Processing Logic (lines 674-716)

```python
should_evolve = response_json["should_evolve"]

if should_evolve:
    actions = response_json["actions"]
    for action in actions:
        if action == "strengthen":
            # Update NEW entry's links and tags
            note.links.extend(suggested_connections)
            note.tags = tags_to_update  # REPLACE
        elif action == "update_neighbor":
            # Update each neighbor's tags and context
            for i, neighbor in enumerate(neighbors):
                neighbor.tags = new_tags_neighborhood[i]  # REPLACE
                neighbor.context = new_context_neighborhood[i]
```

---

## What Memex Currently Does

### Separate LLM Calls (No Unified Decision)

1. **`evolve_neighbors_batched()`** - Updates neighbors only
   - Returns `EvolutionSuggestion` with `new_keywords`, `new_context`
   - No `should_evolve` - always returns suggestions

2. **`analyze_for_strengthen()`** - Updates new entry only
   - Returns `StrengthenResult` with `should_strengthen`, `new_keywords`, `suggested_links`
   - Has its own decision but separate from neighbor evolution

### No Unified `should_evolve` Decision

We use **score threshold** instead of LLM decision:
- If similarity score > threshold → evolve
- No LLM deciding "should this relationship warrant evolution?"

---

## The Gap: What Needs to Change

### 1. New Unified Response Model

Add to `src/memex/models.py`:

```python
class EvolutionDecision(BaseModel):
    """A-Mem unified evolution decision from LLM."""

    should_evolve: bool
    """LLM decides if evolution is warranted."""

    actions: list[str] = Field(default_factory=list)
    """Actions to take: 'strengthen', 'update_neighbor', or both."""

    # For strengthen action (updates NEW entry)
    suggested_connections: list[str] = Field(default_factory=list)
    """Neighbor paths to explicitly link to."""

    new_entry_keywords: list[str] = Field(default_factory=list)
    """Updated keywords for the new entry."""

    # For update_neighbor action (updates EXISTING entries)
    neighbor_updates: list[NeighborEvolution] = Field(default_factory=list)
    """Per-neighbor evolution data."""


class NeighborEvolution(BaseModel):
    """Evolution data for a single neighbor."""

    path: str
    new_keywords: list[str]
    new_context: str
```

### 2. New Unified LLM Function

Add to `src/memex/llm.py`:

```python
async def analyze_evolution(
    new_entry_title: str,
    new_entry_content: str,
    new_entry_keywords: list[str],
    new_entry_context: str,
    neighbors: list[NeighborInfo],
    model: str,
) -> EvolutionDecision:
    """Single LLM call matching A-Mem's unified evolution prompt."""

    # Build prompt matching A-Mem exactly
    # Ask: should_evolve? which actions? update both new entry and neighbors
    # Return EvolutionDecision
```

### 3. Update `process_evolution_items()`

Change `src/memex/core.py`:

```python
# OLD: Always process if score > threshold
suggestions = await evolve_neighbors_batched(...)

# NEW: Respect LLM's should_evolve decision
decision = await analyze_evolution(...)
if not decision.should_evolve:
    continue  # LLM said don't evolve

if "strengthen" in decision.actions:
    # Update new entry keywords and links

if "update_neighbor" in decision.actions:
    # Update neighbors (as we do now)
```

---

## Implementation Checklist

- [ ] Add `NeighborEvolution` model to `models.py`
- [ ] Add `EvolutionDecision` model to `models.py`
- [ ] Add `analyze_evolution()` function to `llm.py` with A-Mem prompt
- [ ] Update `process_evolution_items()` to use unified function
- [ ] Respect `should_evolve=false` (skip evolution entirely)
- [ ] Handle both actions in single flow
- [ ] Add tests for new unified evolution path
- [ ] Remove or deprecate separate `evolve_neighbors_batched()` and `analyze_for_strengthen()`

---

## What Stays the Same

These are already implemented correctly:

- ✅ Keywords REPLACE (not append)
- ✅ Context/description updates
- ✅ Evolution history tracking
- ✅ Retrieval count (views_tracker.py)
- ✅ Keyword extraction via LLM
- ✅ Semantic search via ChromaDB
- ✅ Async queue-based processing (our improvement over A-Mem's synchronous)

---

## Beads Tracking This Work

- `voidlabs-kb-a7rg` - New evolution models (EvolutionDecision)
- `voidlabs-kb-dyr6` - New LLM evolution function (analyze_evolution)
- `voidlabs-kb-p6tk` - Parent epic for full A-Mem parity
