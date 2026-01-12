#!/bin/bash
# Stop/PreCompact hook wrapper for memory capture
# Summarizes session via external LLM and writes to session log
#
# Usage: memory-capture.sh [stop|precompact]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"

# Get trigger type from argument or default to "stop"
TRIGGER="${1:-stop}"

# Run the Python script with uv to ensure dependencies
cd "$PLUGIN_ROOT" && uv run python hooks/memory-capture.py "$TRIGGER"
