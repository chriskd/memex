# voidlabs-kb

Organization-wide knowledge base with semantic search for Claude Code.

## Features

- **Hybrid search** - Combines keyword (Whoosh) and semantic (ChromaDB + sentence-transformers) search
- **MCP tools** - search, add, update, get, list, backlinks, quality, reindex
- **Slash commands** - `/kb search`, `/kb add`, `/kb quality`
- **Session context** - Automatically surfaces relevant KB entries when starting sessions
- **Bidirectional links** - Obsidian-style `[[links]]` with backlink tracking

## Installation

### Option 1: Plugin directory (recommended for development)

```bash
claude --plugin-dir /path/to/voidlabs-kb
```

### Option 2: Copy to project

Copy the entire directory to your project's `.claude-plugin/` folder:

```bash
cp -r /path/to/voidlabs-kb /your/project/.claude-plugin/voidlabs-kb
```

### Option 3: Global installation

Add to your Claude Code settings (`~/.claude/settings.json`):

```json
{
  "plugins": ["/path/to/voidlabs-kb"]
}
```

## Prerequisites

- Python 3.11+
- `uv` package manager (the MCP server uses `uv run`)

Dependencies are installed automatically via `uv` when the MCP server starts.

## Usage

### Searching the KB

```
/kb search kubernetes deployment
```

Or use the MCP tool directly:
```
search("kubernetes deployment")
```

### Adding entries

```
/kb add "Nginx reverse proxy setup"
```

The command will interactively guide you through:
1. Duplicate checking
2. Category selection
3. Content entry
4. Tag assignment

### Checking quality

```
/kb quality
```

Runs search accuracy tests to verify KB content is discoverable.

## Knowledge Base Structure

Entries are stored in `kb/` with this category structure:

```
kb/
├── infrastructure/   # servers, networking, cloud
├── devops/          # CI/CD, monitoring, deployment
├── development/     # coding practices, languages
├── troubleshooting/ # problem solutions
├── architecture/    # system design, patterns
└── patterns/        # reusable solutions
```

Each entry is a Markdown file with YAML frontmatter:

```markdown
---
title: Kubernetes Pod Networking
tags: [kubernetes, networking, infrastructure]
created: 2024-01-15
---

# Kubernetes Pod Networking

Content here...
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `search` | Hybrid keyword + semantic search |
| `add` | Create new KB entry |
| `update` | Modify existing entry |
| `get` | Retrieve entry by path |
| `list` | List entries (optionally by category) |
| `backlinks` | Find entries linking to a given entry |
| `quality` | Run search accuracy tests |
| `reindex` | Rebuild search indices |

## Configuration

The MCP server uses these environment variables (set automatically by the plugin):

- `KB_ROOT` - Path to knowledge base directory (default: `${CLAUDE_PLUGIN_ROOT}/kb`)
- `INDEX_ROOT` - Path to search indices (default: `${CLAUDE_PLUGIN_ROOT}/.indices`)
- `KB_PRELOAD` - Set to `1` to preload the embedding model at startup (reduces first-search latency from ~3s to instant)

To enable preloading, add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "voidlabs-kb": {
      "env": {
        "KB_PRELOAD": "1"
      }
    }
  }
}
```

## Contributor Tracking

When you add or update entries via MCP tools, your git identity is automatically recorded in the entry's `contributors` field. This helps track who has contributed to organizational knowledge.
