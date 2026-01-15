---
title: Strengthen Action Implementation
tags:
  - a-mem
  - evolution
  - implementation
created: 2026-01-15T04:11:04.122294+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
git_branch: strengthen-action
last_edited_by: chris
keywords:
  - strengthen
  - new entry
  - keywords
  - LLM
  - analyze_for_strengthen
---

# Strengthen Action Implementation

The **strengthen** action is part of A-Mem's memory evolution system. While `update_neighbor` evolves existing entries when new connections form, `strengthen` updates the **new entry itself** based on discovered neighbors.

## How It Works

When a new entry is added and linked to existing neighbors:

1. If `strengthen_on_add: true`, `analyze_for_strengthen()` is called
2. LLM analyzes the relationship between new entry and neighbors
3. If LLM returns `should_strengthen: true`, the entry's keywords are updated
4. Suggested links to neighbors may also be added

## Configuration

```yaml
# .kbconfig
memory_evolution:
  enabled: true
  strengthen_on_add: true   # Default: false (opt-in)
  model: anthropic/claude-3-5-haiku
  min_score: 0.7
```

**Conservative default**: `strengthen_on_add: false` because it adds an LLM call to `add_entry()`.

## Key Differences from Neighbor Evolution

| Aspect | Strengthen | Update Neighbor |
|--------|------------|-----------------|
| Target | New entry | Existing neighbors |
| Timing | Synchronous during add | Queued, processed by `mx evolve` |
| Purpose | Refine new entry's keywords | Evolve neighbors' keywords/context |

## Implementation Details

### Files
- `src/memex/llm.py`: `StrengthenResult` dataclass, `analyze_for_strengthen()` function
- `src/memex/config.py`: `strengthen_on_add` config option
- `src/memex/core.py`: Integration in `add_entry()` with error handling

### Error Handling

Strengthen **never blocks** `add_entry()`:
- `LLMConfigurationError` (no API key): Logged at debug level, silently skipped
- Other exceptions: Logged as warning, entry creation continues

### LLM Prompt

The prompt asks the LLM to:
1. Decide if keywords should be refined based on neighbor relationships
2. Suggest updated keywords for the new entry
3. Suggest which neighbors should be explicitly linked

Response format:
```json
{
  "should_strengthen": true,
  "new_keywords": ["kw1", "kw2", "kw3"],
  "suggested_links": ["path/to/neighbor.md"]
}
```

## Status: Complete ✓

The strengthen action is fully integrated into `add_entry()` as of January 2026.

### Integration Flow

1. `add_entry()` creates bidirectional semantic links
2. If neighbors found AND `strengthen_on_add: true`:
   - Build `NeighborInfo` objects from neighbor files
   - Call `analyze_for_strengthen()` with LLM
   - If `should_strengthen: true`:
     - Update entry keywords with refined list
     - Add suggested semantic links (with reason `strengthen_suggested`)
     - Re-save and re-index entry
3. Errors are logged but never block entry creation

### Helper Function

`_build_neighbor_info_for_strengthen()` reads neighbor entries and returns `NeighborInfo` objects for the LLM analysis.

## Testing

### LLM Function Tests (existing)
- `test_analyze_for_strengthen_no_neighbors`
- `test_analyze_for_strengthen_parses_response`
- `test_analyze_for_strengthen_should_not_strengthen`
- `test_analyze_for_strengthen_handles_invalid_json`
- `test_analyze_for_strengthen_filters_invalid_links`

### Config Tests (existing)
- `test_default_config_strengthen_disabled`
- `test_config_loads_strengthen_on_add`
- `test_config_strengthen_explicit_false`

### Integration Tests (new, `TestStrengthenIntegration` class)
- `test_build_neighbor_info_for_strengthen` - Helper reads neighbor data correctly
- `test_build_neighbor_info_skips_missing_files` - Handles missing neighbors gracefully
- `test_strengthen_updates_keywords_when_enabled` - Keywords updated when config enabled
- `test_strengthen_skipped_when_disabled` - No LLM call when config disabled
- `test_strengthen_adds_semantic_links_when_suggested` - Links added from LLM suggestions
- `test_strengthen_respects_should_strengthen_false` - Entry unchanged when LLM says no