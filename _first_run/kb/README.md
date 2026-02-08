---
title: Project Knowledge Base
tags:
  - kb
  - meta
  - project
created: 2026-02-08T07:31:44.106781+00:00
---

# Project Knowledge Base

This directory contains project-specific knowledge base entries managed by `mx`.
Commit this directory to share knowledge with collaborators.

## Usage

```bash
mx add --title="Entry" --tags="tag1,tag2" --content="..." --scope=project
mx search "query" --scope=project
mx list --scope=project
```

## Structure

Entries are Markdown files with YAML frontmatter:

```markdown
---
title: Entry Title
tags: [tag1, tag2]
created: 2024-01-15T10:30:00
---

# Entry Title

Your content here.
```

## Integration

Project KB entries take precedence over global KB entries in search results.
This keeps project-specific knowledge close to the code.
