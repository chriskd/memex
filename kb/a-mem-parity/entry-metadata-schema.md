---
title: Entry Metadata Schema
tags:
  - a-mem
  - schema
  - metadata
  - models
  - features
created: 2026-01-14T23:36:29.356106+00:00
updated: 2026-01-15T02:55:15.146243+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
semantic_links:
  - path: a-mem-parity/semantic-linking.md
    score: 0.683
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-parity-analysis.md
    score: 0.68
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-init-command-specification.md
    score: 0.617
    reason: bidirectional
---

# Entry Metadata Schema

Memex defines the data models for KB entries in `src/memex/models.py`. This documents the A-Mem-related schema additions.

## SemanticLink Model

The `SemanticLink` model represents a computed relationship between entries:

```python
class SemanticLink(BaseModel):
    """A computed semantic relationship to another entry."""

    path: str      # Target entry path (e.g., "guides/python.md")
    score: float   # Similarity score (0.0-1.0)
    reason: str    # How discovered: 'embedding_similarity' | 'bidirectional' | 'shared_tags'
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `path` | `str` | Relative path to the linked entry |
| `score` | `float` | Similarity score between 0 and 1 |
| `reason` | `str` | Discovery method |

### Reason Values

| Reason | Meaning |
|--------|---------|
| `embedding_similarity` | Forward link created from semantic search |
| `bidirectional` | Backlink created when another entry links to this one |
| `shared_tags` | Link based on common tags (future) |
| `manual` | Explicitly specified by user |

## EntryMetadata Model

The `EntryMetadata` model defines frontmatter fields for KB entries. A-Mem adds two new fields:

```python
class EntryMetadata(BaseModel):
    """Frontmatter metadata for a KB entry."""

    title: str
    description: str | None = None
    tags: list[str] = Field(min_length=1)
    created: datetime
    updated: datetime | None = None
    contributors: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    status: Literal["draft", "published", "archived"] = "published"
    source_project: str | None = None
    edit_sources: list[str] = Field(default_factory=list)
    # Breadcrumb metadata
    model: str | None = None
    git_branch: str | None = None
    last_edited_by: str | None = None
    # Beads integration
    beads_issues: list[str] = Field(default_factory=list)
    beads_project: str | None = None
    # A-Mem semantic linking (NEW)
    keywords: list[str] = Field(default_factory=list)
    semantic_links: list[SemanticLink] = Field(default_factory=list)
```

### A-Mem Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `keywords` | `list[str]` | `[]` | LLM-extracted key concepts for embedding enrichment |
| `semantic_links` | `list[SemanticLink]` | `[]` | Computed relationships to other entries |

## Frontmatter Format

In YAML frontmatter, these fields appear as:

```yaml
---
title: My Entry
tags:
  - example
  - guide
created: 2026-01-14T10:30:00+00:00
keywords:
  - REST
  - API design
  - versioning
semantic_links:
  - path: reference/api-patterns.md
    score: 0.78
    reason: embedding_similarity
  - path: guides/http-basics.md
    score: 0.65
    reason: bidirectional
---
```

## CLI Integration

### Adding entries with A-Mem fields

```bash
# With keywords
mx add --title="Guide" --tags="guide"   --keywords="concept1,concept2"   --content="..."

# With manual semantic links
mx add --title="Guide" --tags="guide"   --semantic-links='[{"path": "ref/other.md", "score": 0.8, "reason": "manual"}]'   --content="..."
```

### Updating A-Mem fields

```bash
# Update keywords
mx replace guides/my-guide.md --keywords="new1,new2,new3"

# Update semantic links (replaces existing)
mx replace guides/my-guide.md   --semantic-links='[{"path": "ref/new.md", "score": 0.9, "reason": "manual"}]'
```

## Auto-Population

When `SEMANTIC_LINK_ENABLED=True` (default), semantic_links are auto-populated:

1. **On add**: After indexing, find similar entries and create bidirectional links
2. **On update**: When content changes, re-compute semantic links

Manual links (`--semantic-links` flag) skip auto-population.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `SEMANTIC_LINK_ENABLED` | `True` | Enable auto-linking |
| `SEMANTIC_LINK_MIN_SCORE` | `0.6` | Minimum similarity threshold |
| `SEMANTIC_LINK_K` | `5` | Maximum neighbors to link |

## Programmatic Access

```python
from memex.models import EntryMetadata, SemanticLink
from memex.parser import parse_entry

# Parse entry to get metadata
metadata, content, chunks = parse_entry(Path("kb/guides/example.md"))

# Access A-Mem fields
print(metadata.keywords)        # ['concept1', 'concept2']
print(metadata.semantic_links)  # [SemanticLink(...), ...]

# Create new semantic link
link = SemanticLink(
    path="ref/other.md",
    score=0.85,
    reason="embedding_similarity",
)
```

## Validation

- `keywords`: Any list of strings (no validation on content)
- `semantic_links`: Must be valid `SemanticLink` objects with all required fields
- `score`: Should be 0.0-1.0 but not enforced at model level
- `reason`: Any string, conventionally one of the standard values

## Edge Cases

- **Empty lists**: Both fields default to empty lists, not None
- **Missing in frontmatter**: Parsed as empty lists
- **Invalid JSON**: `--semantic-links` with malformed JSON raises parse error
- **Unknown fields in SemanticLink**: Extra fields are ignored (Pydantic default)
- **Score precision**: Scores are rounded to 3 decimal places on auto-link creation