# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **MCP Server**: Full Model Context Protocol support via FastMCP
  - `search`: Hybrid keyword + semantic search with RRF ranking
  - `get`: Retrieve entries with metadata, content, links, and backlinks
  - `add`: Create new entries with auto-generated slugs
  - `update`: Modify entries with section-level updates
  - `list`: Browse entries by category, tag, or recency
  - `tree`: Explore KB directory structure
  - `suggest_links`: Find semantically related entries
  - `health`: Audit KB for orphans, broken links, stale content

- **CLI** (`mx`): Token-efficient command-line interface
  - All MCP operations available as shell commands
  - Designed for automation and scripting
  - Minimal output format reduces context usage

- **Web Explorer** (`memex-web`): Visual knowledge browser
  - Interactive search with live results
  - Graph visualization of entry connections
  - Directory tree navigation
  - Markdown rendering with syntax highlighting

- **Hybrid Search**: Best-of-both-worlds search approach
  - BM25 keyword search via Whoosh
  - Semantic search via ChromaDB + sentence-transformers
  - Reciprocal Rank Fusion (RRF) for result merging
  - Context-aware boosting for project relevance

- **Bidirectional Links**: Wiki-style `[[link]]` syntax
  - Auto-resolved to existing entries
  - Backlink tracking across the KB
  - Stale link detection in health checks

### Technical

- Python 3.11+ with type hints throughout
- Pydantic models for all data structures
- Async-first architecture
- Configurable via environment variables
