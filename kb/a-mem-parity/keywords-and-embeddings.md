---
title: Keywords and Embeddings
tags:
  - a-mem
  - keywords
  - embeddings
  - search
  - features
created: 2026-01-14T23:35:46.279714+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
git_branch: main
last_edited_by: chris
semantic_links:
  - path: a-mem-parity/semantic-linking.md
    score: 0.625
    reason: embedding_similarity
---

# Keywords and Embeddings

Memex enriches document embeddings with keywords and tags, following the A-Mem approach of semantic context enhancement for improved search quality.

## Overview

When documents are indexed, memex builds enriched text for embedding by concatenating:
1. **Document content** - The main markdown body
2. **Keywords** - LLM-extracted key concepts from metadata
3. **Tags** - Document tags from frontmatter

This produces embeddings that capture both content semantics and categorical/conceptual context.

## CLI Usage

### Adding entries with keywords

```bash
# Add entry with keywords
mx add --title="API Design Guide" --tags="api,design"   --keywords="REST,GraphQL,versioning,rate-limiting"   --content="..."

# Keywords are comma-separated
mx add --title="Python Patterns" --tags="python"   --keywords="decorators,context managers,generators"   --content="..."
```

### Updating entries with keywords

```bash
# Replace entry with new keywords
mx replace guides/api.md --keywords="REST,gRPC,OpenAPI"

# Update entry (deprecated alias)
mx update guides/api.md --keywords="REST,gRPC,OpenAPI"
```

## How Embedding Enrichment Works

The `_build_embedding_text` function in `chroma_index.py` builds the text sent to the embedding model:

```python
def _build_embedding_text(self, content: str, keywords: list[str], tags: list[str]) -> str:
    parts = [content]
    if keywords:
        parts.append(f"

Keywords: {', '.join(keywords)}")
    if tags:
        parts.append(f"
Tags: {', '.join(tags)}")
    return "".join(parts)
```

This means a document with:
- Content: "Guide to building REST APIs..."
- Keywords: ["\REST", "versioning"]
- Tags: ["api", "design"]

Gets embedded as:
```
Guide to building REST APIs...

Keywords: REST, versioning
Tags: api, design
```

## Benefits

1. **Improved semantic search** - Queries for "versioning" find entries with that keyword even if the content doesn't prominently feature the term
2. **Category-aware similarity** - Entries with similar tags cluster together in embedding space
3. **LLM-extracted concepts** - Keywords capture high-level concepts that may be implicit in content

## When to Use Keywords

| Use Case | Example Keywords |
|----------|------------------|
| Technical concepts | "microservices", "event-driven", "CQRS" |
| Domain terms | "kubernetes", "terraform", "AWS" |
| Abstract themes | "scalability", "security", "performance" |
| Related but unmentioned | Concepts the entry relates to but doesn't explicitly discuss |

## Edge Cases

- **Empty keywords**: If no keywords provided, only content and tags are embedded
- **Duplicate keywords**: Duplicates in the keyword list are preserved (no deduplication)
- **Special characters**: Keywords with special characters are embedded as-is
- **Re-indexing**: When keywords change, the entry is re-indexed with the new embedding

## Integration with Auto-Linking

Keywords influence semantic similarity scores used for auto-linking. Entries with overlapping keywords will have higher embedding similarity, making them more likely to be automatically linked.

```bash
# Entry A: keywords="REST,API,versioning"
# Entry B: keywords="REST,OpenAPI,documentation"
# -> Higher similarity due to shared "REST" keyword
```

## Programmatic API

```python
from memex.core import add_entry, update_entry

# Add with keywords
await add_entry(
    title="My Guide",
    content="...",
    tags=["guide"],
    category="guides",
    keywords=["concept1", "concept2", "concept3"],
)

# Update with new keywords
await update_entry(
    path="guides/my-guide.md",
    keywords=["new-concept", "updated-term"],
)
```