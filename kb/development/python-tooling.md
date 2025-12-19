---
title: Python Development with uv
tags:
  - python
  - uv
  - tooling
created: 2024-12-19
contributors:
  - agent
---

# Python Development with uv

**Use `uv` for all Python package management** - not pip, poetry, or pipenv.

## Why uv?

- Fast dependency resolution (written in Rust)
- Drop-in pip replacement
- Handles virtual environments
- Lockfile support for reproducible builds

## Essential Commands

```bash
# Create virtual environment
uv venv

# Activate it (optional, uv commands work without activation)
source .venv/bin/activate

# Install dependencies from pyproject.toml
uv pip install -e ".[dev]"

# Add new dependency
uv add fastapi

# Sync from lockfile (reproducible install)
uv sync

# Update lockfile
uv lock
```

## Virtual Environment Rules

**Virtual environments are mandatory.** Always:
- Create `.venv/` in the project root
- Never install packages globally
- Commit `uv.lock` to version control
- Add `.venv/` to `.gitignore`

## Code Quality

Run these before committing:

```bash
# Format and lint
ruff check --fix .
ruff format .

# Type check (if using types)
pyright

# Tests
pytest
```

## Related

- [[development/project-structure]] - Where files go
- [[devops/docker-patterns]] - Using uv in Docker
