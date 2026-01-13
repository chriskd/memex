---
title: Agent Memory
tags:
  - agent-memory
  - hooks
  - claude-code
  - sessions
created: 2026-01-13T00:02:55.930011+00:00
updated: 2026-01-13
---

# Agent Memory

Automatic session memory capture and injection for Claude Code. Remembers what you worked on across sessions without manual effort.

## Quick Start

```bash
# 1. Enable memory for this project
mx memory init

# 2. That's it! Memory is now active.
#    - Sessions auto-captured when you exit
#    - Context auto-injected when you start
```

## Commands

| Command | Description |
|---------|-------------|
| `mx memory` | Show memory status |
| `mx memory init` | Enable memory for this project |
| `mx memory init --user` | Enable memory user-wide |
| `mx memory add "note"` | Add a manual memory note |
| `mx memory inject` | Preview what would be injected |
| `mx memory capture` | Manually trigger capture |
| `mx memory disable` | Remove memory hooks |

## How It Works

### Automatic Capture (Stop/PreCompact)

When you end a session or context compacts:

1. Hook reads your conversation from `~/.claude/projects/`
2. Calls Claude haiku to extract structured observations
3. Writes to today's session file: `kb/sessions/2026-01-12.md`

**Observation categories extracted:**
- `[learned]` - New knowledge or insights
- `[decision]` - Choices made and why
- `[pattern]` - Recurring approaches or conventions
- `[issue]` - Problems encountered
- `[todo]` - Follow-up work identified

### Automatic Injection (SessionStart)

When you start a Claude Code session:

1. Hook reads recent session files from `kb/sessions/`
2. Formats ~1000 tokens of relevant context
3. Outputs as system reminder

**Example injection:**
```
## Recent Memory (myproject)

**2h ago:** Fixed authentication bug in login flow
- [learned] OAuth tokens expire after 1 hour, need refresh logic
- [decision] Use httpx instead of requests for async support

**yesterday:** Refactored database connection pooling
- [pattern] Connection pools should be initialized once at startup
```

## Configuration

### .kbconfig

```yaml
# Required
kb_path: kb

# Memory settings (set by mx memory init)
session_dir: sessions              # Where session files go
session_retention_days: 30         # Auto-cleanup after N days
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | API key for haiku summarization |
| `CLAUDE_PROJECT_DIR` | Auto | Set by Claude Code hooks |
| `CLAUDE_SESSION_ID` | Auto | Set by Claude Code hooks |

## Session Files

Sessions are stored as per-day markdown files:

```
kb/sessions/
  2026-01-12.md
  2026-01-11.md
  2026-01-10.md
```

Each file contains multiple session entries:

```markdown
---
title: Session Log 2026-01-12
tags: [sessions, memory]
created: 2026-01-12T10:00:00
---

# Session Log - 2026-01-12

## 2026-01-12 10:30 UTC

Implemented user authentication with OAuth2.

### Observations
- [learned] OAuth tokens need refresh logic
- [decision] Using httpx for async HTTP
- [pattern] Store tokens in httponly cookies

### Files
- src/auth.py
- tests/test_auth.py

## 2026-01-12 15:00 UTC

Fixed rate limiting bug in API.
...
```

## Manual Notes

Add notes without waiting for auto-capture:

```bash
# Quick note
mx memory add "Fixed auth bug using refresh tokens"

# With tags
mx memory add "Deployed v2.0" --tags=deployment,release

# From file
mx memory add --file=notes.md
```

## Troubleshooting

### Check Status

```bash
mx memory status
```

Shows:
- Whether hooks are installed
- Session directory configuration
- API key status

### "Hooks not installed"

Run `mx memory init` to install hooks.

### "API key not set"

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Preview Injection

```bash
mx memory inject
```

Shows what context would be injected at session start.

## Architecture

```
SessionStart Hook
       │
       ▼
┌─────────────────┐
│ mx memory inject│ ─── reads ──▶ kb/sessions/*.md
└────────┬────────┘
         │
         ▼
  System Reminder
  (injected ctx)


Stop/PreCompact Hook
       │
       ▼
┌──────────────────┐      ┌─────────────┐
│ mx memory capture│ ───▶ │Claude Haiku │
└────────┬─────────┘      │(summarize)  │
         │                └─────────────┘
         ▼
  kb/sessions/2026-01-12.md
```

## See Also

- [[guides/ai-integration]] - General AI agent setup
- [[reference/cli]] - CLI command reference
