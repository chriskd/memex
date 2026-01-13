---
title: Agent Memory
tags:
  - agent-memory
  - hooks
  - claude-code
  - sessions
created: 2026-01-13T00:02:55.930011+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
git_branch: main
last_edited_by: chris
---

# Agent Memory

Automatic session memory capture and injection for Claude Code. Remembers what you worked on across sessions without manual effort.

## Overview

Agent Memory consists of two hooks that run automatically:

1. **Memory Injection** (SessionStart) - Injects recent session context when you start Claude Code
2. **Memory Capture** (Stop/PreCompact) - Summarizes your session via Claude haiku when you finish

This gives Claude awareness of recent work without polluting your context window with lengthy instructions.

## Quick Start

### Prerequisites

1. **ANTHROPIC_API_KEY** - Required for LLM summarization
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

2. **Project .kbconfig** - Must have `primary:` set for session log path
   ```yaml
   # .kbconfig
   kb_path: kb
   primary: projects/myproject
   ```

3. **Dependencies installed**
   ```bash
   uv sync  # Installs anthropic, pyyaml
   ```

### Verify Setup

Test injection (shows what would be injected at session start):
```bash
CLAUDE_PROJECT_DIR=/path/to/project uv run python hooks/memory-inject.py
```

Test capture (summarizes current session):
```bash
CLAUDE_PROJECT_DIR=/path/to/project CLAUDE_SESSION_ID=<session-id> uv run python hooks/memory-capture.py stop
```

## How It Works

### Session Start (Injection)

When you start a Claude Code session:

1. Hook reads your project's `.kbconfig` to find the KB
2. Locates session log at `{primary}/sessions.md`
3. Parses recent session entries
4. Formats ~1000 tokens of context
5. Outputs as system reminder

**Example injection output:**
```
## Recent Memory (myproject)

**2h ago:** Fixed authentication bug in login flow
- [learned] OAuth tokens expire after 1 hour, need refresh logic
- [decision] Use httpx instead of requests for async support
- Files: src/auth.py, tests/test_auth.py

**yesterday:** Refactored database connection pooling
- [pattern] Connection pools should be initialized once at startup
```

### Session End (Capture)

When you end a session or context compacts:

1. Hook finds your session's JSONL file in `~/.claude/projects/`
2. Parses recent conversation messages
3. Calls Claude haiku to extract structured observations
4. Writes to session log via `mx session-log`

**Observation categories:**
- `[learned]` - New knowledge or insights
- `[decision]` - Choices made and why
- `[pattern]` - Recurring approaches or conventions
- `[issue]` - Problems encountered
- `[todo]` - Follow-up work identified

## Configuration

### .kbconfig (Required)

```yaml
# Path to KB directory
kb_path: kb

# Primary directory - session log goes here
primary: projects/myproject

# Optional: explicit session entry path
# session_entry: projects/myproject/devlog.md
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | API key for haiku summarization |
| `CLAUDE_PROJECT_DIR` | Auto | Set by Claude Code hooks |
| `CLAUDE_SESSION_ID` | Auto | Set by Claude Code hooks |
| `MEMEX_KB_ROOT` | No | Override KB location |

### Hook Configuration (hooks/hooks.json)

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/memory-inject.sh",
        "timeout": 30000
      }]
    }],
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/memory-capture.sh stop",
        "timeout": 60000
      }]
    }],
    "PreCompact": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/memory-capture.sh precompact",
        "timeout": 60000
      }]
    }]
  }
}
```

### Tuning Parameters

In `memory-inject.py`:
```python
MAX_RECENT_SESSIONS = 5      # How many sessions to show
MAX_TOKENS_BUDGET = 1000     # Approximate token limit
CACHE_TTL_SECONDS = 300      # Cache duration (5 min)
```

In `memory-capture.py`:
```python
MAX_MESSAGES = 100           # Messages to include in summary
MIN_MESSAGES = 3             # Skip tiny sessions
MIN_CONTENT_LENGTH = 500     # Skip trivial sessions
```

## Troubleshooting

### "No previous sessions recorded"

1. Check `.kbconfig` has `primary:` set
2. Verify session log exists: `mx get {primary}/sessions.md`
3. Run a test capture to create initial entry

### Capture not working

1. Check `ANTHROPIC_API_KEY` is set
2. Verify session file exists:
   ```bash
   ls ~/.claude/projects/-path-to-project/*.jsonl
   ```
3. Run capture manually with debug:
   ```bash
   CLAUDE_PROJECT_DIR=/path/to/project    CLAUDE_SESSION_ID=<id>    uv run python hooks/memory-capture.py stop
   ```

### Worktree issues

Memory hooks handle git worktrees by checking parent paths. If in `.worktrees/branch-name`, the hook tries both:
- Current path: `/project/.worktrees/branch`  
- Parent path: `/project`

## Session Log Format

Entries are appended to `{primary}/sessions.md`:

```markdown
## 2026-01-12 23:38 UTC

Brief summary of what was accomplished in the session.

### Observations
- [learned] Something new discovered
- [decision] Choice made and rationale
- [pattern] Recurring approach identified
- [issue] Problem encountered
- [todo] Follow-up work needed

### Files
- src/feature.py
- tests/test_feature.py
```

## Manual Session Logging

You can also log manually without the hooks:

```bash
# Quick note
mx session-log -m "Fixed the auth bug, added refresh token logic"

# With tags
mx session-log -m "Deployed v2.0" --tags="deployment,release"

# From file
mx session-log --file=session-notes.md
```

## Architecture

```
âââââââââââââââââââ     ââââââââââââââââââââ
â  SessionStart   ââââââ¶â memory-inject.py â
â     Hook        â     â  (reads KB)      â
âââââââââââââââââââ     ââââââââââ¬ââââââââââ
                                 â
                                 â¼
                        ââââââââââââââââââ
                        â System Reminderâ
                        â (injected ctx) â
                        ââââââââââââââââââ

âââââââââââââââââââ     ââââââââââââââââââââ     âââââââââââââââ
â  Stop/PreCompactââââââ¶âmemory-capture.py ââââââ¶âClaude Haiku â
â     Hook        â     â (reads session)  â     â(summarize)  â
âââââââââââââââââââ     ââââââââââ¬ââââââââââ     âââââââââââââââ
                                 â
                                 â¼
                        ââââââââââââââââââ
                        â mx session-log â
                        â  (writes KB)   â
                        ââââââââââââââââââ
```

## See Also

- [[guides/ai-integration]] - General AI agent setup
- [[reference/cli]] - CLI command reference
- [[guides/quick-start]] - Getting started with memex
