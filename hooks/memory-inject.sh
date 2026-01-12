#!/bin/bash
# SessionStart hook wrapper for memory injection
# Injects recent session context into new Claude Code sessions

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"

# Run the Python script with uv to ensure dependencies
cd "$PLUGIN_ROOT" && uv run python hooks/memory-inject.py
