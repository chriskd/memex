---
title: A-Mem Strict Mode
tags:
  - a-mem
  - configuration
  - keywords
  - enforcement
created: 2026-01-15T01:24:33.930558+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
git_branch: main
last_edited_by: chris
keywords:
  - amem_strict
  - kbconfig
  - keywords
  - enforcement
  - LLM
  - validation
  - error message
semantic_links:
  - path: a-mem-parity/keywords-and-embeddings.md
    score: 0.651
    reason: embedding_similarity
---

# A-Mem Strict Mode

Enforcement mode that requires keywords on all KB entries, improving semantic linking effectiveness.

## Problem

When LLMs use `mx add`, they often forget to populate the `--keywords` field even though it exists. This reduces the effectiveness of A-Mem-style semantic linking and search.

## Solution

Add `amem_strict: true` to your `.kbconfig` file:

```yaml
kb_path: kb
amem_strict: true
```

## Behavior

### When disabled (default)
Keywords are optional - current behavior unchanged.

### When enabled
- `mx add` without `--keywords` fails with helpful error
- `mx replace` with content changes fails if entry lacks keywords
- Tag-only updates still work without keywords
- Entries that already have keywords can be updated without providing new ones

## Error Message

When strict mode blocks an operation, a helpful error teaches the pattern:

```
Error: A-Mem strict mode is enabled but --keywords was not provided.

To fix this, add keywords that capture key concepts in your entry:

    mx add --title="Your Title"            --tags="tag1,tag2"            --keywords="concept1,concept2,concept3"            --content="..."

Keywords should be:
  â¢ Key concepts mentioned in the content (e.g., "REST", "caching")
  â¢ Related terms not explicitly mentioned (e.g., "API design")
  â¢ Domain-specific terminology (e.g., "microservices")

Typically 3-7 keywords work well.
```

## Implementation

- Config: `is_amem_strict_enabled()` in `config.py`
- Validation: Checks in `add_entry()` and `update_entry()` in `core.py`
- Error: `AMEMStrictError` exception with `AMEM_STRICT_ERROR_MESSAGE`

## See Also

- [[a-mem-parity/keywords-and-embeddings.md|Keywords and Embeddings]] - How keywords improve search
- [[a-mem-parity/semantic-linking.md|Semantic Linking]] - Auto-linking based on similarity