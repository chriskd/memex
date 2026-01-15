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

## Testing

8 tests in `tests/test_memory_evolution.py`:
- `test_analyze_for_strengthen_no_neighbors`
- `test_analyze_for_strengthen_parses_response`
- `test_analyze_for_strengthen_should_not_strengthen`
- `test_analyze_for_strengthen_handles_invalid_json`
- `test_analyze_for_strengthen_filters_invalid_links`
- `test_default_config_strengthen_disabled`
- `test_config_loads_strengthen_on_add`
- `test_config_strengthen_explicit_false`