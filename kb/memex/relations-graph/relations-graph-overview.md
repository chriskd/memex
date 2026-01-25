---
title: Relations Graph Overview
tags:
  - memex
  - relations
  - graph
created: 2026-01-15T06:32:04.180518+00:00
updated: 2026-01-25T19:15:11+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
git_branch: relations-field
last_edited_by: chris
relations:
  - path: memex/relations-graph/wikilink-edge-behavior.md
    type: implements
  - path: memex/relations-graph/frontmatter-edge-types.md
    type: depends_on
---


# Relations Graph Overview

This page connects wikilinks and typed relations into a single graph.

See [[memex/relations-graph/wikilink-edge-behavior]] and [[memex/relations-graph/frontmatter-edge-types]] for details.

## Published UI

Published KB pages surface typed relations in two places:

- **Entry panel**: "Typed Relations" shows outgoing vs incoming edges with direction arrows and type labels.
- **Graph view**: Typed relations render as solid edges with arrowheads, and the controls let you filter by origin and relation type.

## Search neighbors

`mx search --include-neighbors` expands results using both semantic links and typed relations.
Use `--neighbor-depth` to control hop count (default 1).

## Query the relations graph

Use `mx relations` to inspect the unified graph (wikilinks + typed relations).

```bash
mx relations path/to/entry.md
mx relations path/to/entry.md --depth=2 --direction=outgoing
mx relations path/to/entry.md --origin=relations --type=depends_on
mx relations --graph --json
```

## Editing typed relations

Use `mx relations-add` and `mx relations-remove` to update frontmatter relations without replacing the full entry.

```bash
mx relations-add path/to/entry.md --relation reference/cli.md=documents
mx relations-add path/to/entry.md --relations='[{"path":"ref/other.md","type":"implements"}]'
mx relations-remove path/to/entry.md --relation reference/cli.md=documents
```
