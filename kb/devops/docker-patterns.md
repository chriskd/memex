---
title: Dockerfile Patterns
tags:
  - docker
  - deployment
  - uv
created: 2024-12-19
contributors:
  - agent
---

# Dockerfile Patterns

Standard Dockerfile for Python/FastAPI apps using uv.

## Production Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/

# Run with uv
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Key Patterns

### Layer Caching

Copy dependency files before source code:

```dockerfile
# Dependencies change less often - cached layer
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Source changes often - rebuilds only from here
COPY src/ ./src/
```

### Frozen Dependencies

Always use `--frozen` in production:

```bash
uv sync --frozen --no-dev
```

This ensures the exact versions from `uv.lock` are installed, no resolution step.

### No Dev Dependencies

Use `--no-dev` in production to skip test/lint tools:

```bash
uv sync --frozen --no-dev
```

### Running with uv

Use `uv run` to execute in the virtual environment:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Multi-Stage Builds (Optional)

For smaller images when build tools are needed:

```dockerfile
# Build stage
FROM python:3.12-slim AS builder
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Related

- [[devops/deployment]] - Dokploy deployment workflow
- [[development/python-tooling]] - Local development with uv
