---
title: Installation Guide
tags: [installation, setup, getting-started]
created: 2026-01-06
description: How to install memex and its semantic search dependencies
---

# Installation Guide

Memex installs with keyword search enabled by default (Whoosh).
Semantic search (ChromaDB + sentence-transformers) is optional via the `search` extra.

## Install (Recommended)

```bash
# With uv (recommended)
uv tool install memex-kb

# With pip
pip install memex-kb

# Verify installation
mx --version
```

This includes:
- Keyword search (Whoosh)
- KB health checks and graph tooling
- Static site publishing (`mx publish`)

## Semantic Search (Optional)

If you want semantic search, install the `search` extra (larger footprint; may download models on first use):

```bash
uv tool install 'memex-kb[search]'
# or
pip install 'memex-kb[search]'
```

## From Source

For development or customization:

```bash
git clone https://github.com/chriskd/memex-kb.git
cd memex

# Runtime dependencies
uv sync

# Dev dependencies
uv sync --dev
```

## GPU Support (Optional)

If you have an NVIDIA GPU and want CUDA acceleration:

```bash
uv sync --index pytorch-gpu=https://download.pytorch.org/whl/cu124
```

## Platform Notes

- **ARM64 (Apple Silicon)**: ChromaDB capped at <1.0.0 for onnxruntime compatibility
- **CPU-only default**: PyTorch configured for CPU to minimize install size
- **Python requirement**: 3.11 or higher

## Next Steps

After installation:
1. [[guides/quick-start|Quick Start Guide]] - Create your first KB
2. [[reference/cli|CLI Reference]] - Full command documentation
3. [[guides/ai-integration|AI Agent Integration]] - Configure AI assistants
