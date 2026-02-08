---
title: Tickets (tk)
tags:
  - reference
  - process
  - tickets
created: 2026-02-08T00:00:00Z
description: How tickets are stored in .tickets/ and managed with tk.
---

# Tickets (tk)

This repo uses `tk`, a minimal ticket system, with tickets stored as Markdown files in `.tickets/`.

## Common Commands

```bash
tk list
tk show <id>
tk start <id>
tk add-note <id> "note text"
tk close <id>
```

`tk` supports partial ID matching (for example, `tk show 822a`).

## File Format

Tickets are plain Markdown with YAML frontmatter at the top:

```yaml
---
id: mem-822a
status: open            # open | in_progress | closed
type: task              # bug | feature | task | epic | chore
priority: 2             # 0-4, 0=highest
assignee:
created: 2026-02-08
deps: []                # optional dependency ticket IDs
links: []               # optional related ticket IDs
tags: [cli, docs]       # optional tags
---
```

Then a Markdown body (problem statement, acceptance criteria, notes, etc.).

## Conventions

- Use the ticket body for acceptance criteria and implementation notes.
- Use `deps:` for true blocking dependencies; use `links:` for related work.
- Prefer small, closeable tickets over long-running mega-tickets.

