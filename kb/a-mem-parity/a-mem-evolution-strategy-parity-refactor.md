---
title: A-Mem Evolution Strategy Parity Refactor
tags:
  - a-mem
  - refactor
  - evolution
  - architecture
created: 2026-01-15T03:36:01.802550+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
git_branch: main
last_edited_by: chris
keywords:
  - evolution-strategy
  - tag-replacement
  - context-update
  - should-evolve
  - neighbor-processing
semantic_links:
  - path: a-mem-parity/a-mem-parity-analysis.md
    score: 0.775
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-test-cases-for-agent-evaluation.md
    score: 0.71
    reason: embedding_similarity
  - path: reference/agent-memory-comparison.md
    score: 0.662
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-strict-mode.md
    score: 0.653
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-init-command-specification.md
    score: 0.643
    reason: embedding_similarity
---

# A-Mem Evolution Strategy Parity Refactor

Refactor mx memory evolution to exactly match A-Mem's strategy.

## Current vs A-Mem Strategy

| Aspect | Current mx | A-Mem | Change Required |
|--------|-----------|-------|-----------------|
| Keyword update | **Append** up to 3 keywords | **Replace** entire list | Yes - major |
| Context/description | Store relationship string | **Replace** context entirely | Yes - major |
| Should evolve decision | Always evolve if score > threshold | **LLM decides** per neighbor | Yes |
| Max keywords | Capped at 3 per evolution | No cap (LLM decides full list) | Remove cap |
| Neighbors processed | 5 | 5 | No change |

## A-Mem Evolution Prompt (from source)

```python
_evolution_system_prompt = """
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
   2.1 If choose to strengthen the connection, which memory should it be connected to? 
       Can you give the updated tags of this memory?
   2.2 If choose to update_neighbor, you can update the context and tags of these memories 
       based on the understanding of these memories.

Return your decision in JSON format:
{
    "should_evolve": True or False,
    "actions": ["strengthen", "update_neighbor"],
    "suggested_connections": ["neighbor_memory_ids"],
    "tags_to_update": ["tag_1",..."tag_n"], 
    "new_context_neighborhood": ["new context",...,"new context"],
    "new_tags_neighborhood": [["tag_1",...,"tag_n"],...["tag_1",...,"tag_n"]]
}
"""
```

## Required Changes

### 1. New Evolution Model

**File**: `src/memex/models.py`

```python
@dataclass
class EvolutionDecision:
    """LLM decision about whether and how to evolve memories."""
    should_evolve: bool
    actions: list[str]  # ["strengthen", "update_neighbor"]
    suggested_connections: list[str]  # Paths to link to
    new_tags: list[str]  # Updated tags for the NEW entry
    neighbor_updates: list[NeighborUpdate]  # Updates for each neighbor

@dataclass  
class NeighborUpdate:
    """Complete replacement data for a neighbor entry."""
    path: str
    new_keywords: list[str]  # Full replacement, not additions
    new_context: str  # Full replacement for description field
```

### 2. New LLM Function

**File**: `src/memex/llm.py`

Replace `evolve_single_neighbor()` and `evolve_neighbors_batched()` with:

```python
async def analyze_evolution(
    new_entry_content: str,
    new_entry_context: str,  # description field
    new_entry_keywords: list[str],
    neighbors: list[NeighborInfo],  # path, content, context, keywords
    model: str,
) -> EvolutionDecision:
    """Analyze new entry and neighbors, return evolution decision.
    
    Uses A-Mem's exact prompt structure to decide:
    1. Should evolution happen at all?
    2. What connections to strengthen?
    3. What new tags for the new entry?
    4. What replacement keywords/context for each neighbor?
    """
```

### 3. Update Core Evolution

**File**: `src/memex/core.py`

Change `process_evolution_items()`:

```python
# OLD: Append keywords
new_keywords = [kw for kw in suggestion.add_keywords if kw not in existing]
updated_keywords = existing + new_keywords

# NEW: Replace keywords entirely
updated_keywords = decision.neighbor_updates[i].new_keywords

# OLD: Store relationship (unused)
# NEW: Replace description
updated_description = decision.neighbor_updates[i].new_context
```

### 4. Update Entry Frontmatter

When evolution runs, update both `keywords` AND `description` fields:

```python
await update_entry(
    path=neighbor_path,
    keywords=new_keywords,      # Full replacement
    description=new_context,    # Full replacement
)
```

### 5. Remove max_keywords_per_neighbor

**File**: `src/memex/config.py`

- Remove `max_keywords_per_neighbor` from `MemoryEvolutionConfig`
- Update `.kbconfig` schema docs

### 6. Add "strengthen" Action Support

A-Mem has two actions:
- `strengthen`: Add links from new entry to suggested neighbors, update new entry's tags
- `update_neighbor`: Replace keywords/context on neighbor entries

We currently only do the equivalent of `update_neighbor`. Need to add:

```python
if "strengthen" in decision.actions:
    # Update the NEW entry's semantic_links to include suggested_connections
    # Update the NEW entry's tags to decision.new_tags
    await update_entry(
        path=new_entry_path,
        semantic_links=existing_links + new_links,
        tags=decision.new_tags,
    )
```

## Migration Considerations

### Backwards Compatibility

- Old evolution queue items will fail with new code (different expected response format)
- Run `mx evolve --clear` before deploying, or handle gracefully

### Risk: Information Loss

A-Mem's "replace" strategy can lose keywords if LLM makes poor decisions.

Mitigations:
1. Log old keywords before replacement
2. Store evolution history (like A-Mem's `evolution_history` field)
3. Consider hybrid: replace but keep unique old keywords

### Testing

- Mock LLM responses in new format
- Test keyword replacement (not append)
- Test context/description updates
- Test "strengthen" action (link creation)
- Test "should_evolve: false" case (no updates)

## Implementation Order

1. **Phase 1**: New models (`EvolutionDecision`, `NeighborUpdate`)
2. **Phase 2**: New LLM function with A-Mem prompt
3. **Phase 3**: Update `process_evolution_items()` to use new format
4. **Phase 4**: Add "strengthen" action support
5. **Phase 5**: Remove deprecated config, update tests
6. **Phase 6**: Add evolution history tracking (optional)

## Success Criteria

1. Evolution prompt matches A-Mem's structure exactly
2. Keywords are replaced, not appended
3. Description field is updated during evolution
4. LLM decides `should_evolve` (not just score threshold)
5. Both `strengthen` and `update_neighbor` actions work
6. No `max_keywords_per_neighbor` constraint

## Related

- [[a-mem-parity/memory-evolution-queue-architecture.md]] - Current queue design
- [[a-mem-parity/keywords-and-embeddings.md]] - How keywords affect embeddings
