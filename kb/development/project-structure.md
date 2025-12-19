---
title: Standard Project Structure
tags:
  - python
  - project-layout
  - conventions
created: 2024-12-19
contributors:
  - agent
---

# Standard Project Structure

All Python projects follow this layout:

```
project/
├── pyproject.toml      # Dependencies and project metadata
├── uv.lock             # Lockfile (commit this)
├── .venv/              # Virtual environment (gitignored)
├── src/                # Source code
│   └── app/            # Application package
│       ├── __init__.py
│       └── main.py
├── tests/              # Test files
├── .devcontainer/      # Devcontainer configuration
├── Dockerfile          # Production build
└── README.md           # Project documentation
```

## Key Files

### pyproject.toml

Project metadata and dependencies:

```toml
[project]
name = "my-project"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi",
    "uvicorn",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "ruff",
    "pyright",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### uv.lock

Generated lockfile - always commit this. Ensures reproducible installs across environments.

### .venv/

Local virtual environment - always gitignored. Created with `uv venv`.

## Creating New Projects

Use the voidlabs-devtools template:

```bash
/srv/fast/code/voidlabs-devtools/scripts/new-project.sh <project-name> <target-dir>
```

This scaffolds the full structure including devcontainer setup.

## Related

- [[development/python-tooling]] - Package management with uv
- [[infrastructure/devcontainers]] - Development container setup
