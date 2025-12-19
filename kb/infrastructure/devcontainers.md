---
title: Devcontainer Setup
tags:
  - devcontainer
  - docker
  - infrastructure
created: 2024-12-19
contributors:
  - agent
---

# Devcontainer Setup

Development happens in **devcontainers** running on `docker.voidlabs.local` (a remote Docker host), not on the local Mac.

## Architecture

```
+-------------+    Mutagen     +-------------------------+
|    Mac      | ----sync-----> |  docker.voidlabs.local  |
|   (beta)    |                |       (alpha)           |
|             |                |                         |
|  Cursor ----+-- SSH remote ->|  +------------------+   |
|  Claude     |                |  |  devcontainer    |   |
|  Codex      |                |  |  /srv/fast/code  |   |
+-------------+                |  +------------------+   |
                               +-------------------------+
```

## Key Implications

- **"Local" means the container** - Commands run inside devcontainers on docker.voidlabs.local
- **Code lives at `/srv/fast/code/`** - This is bind-mounted into containers
- **Docker builds are fast** - Images build on docker.voidlabs.local, no network overhead for layers
- **Mutagen sync has slight delays** - If a file seems stale after editing, wait a moment
- **SSH agent forwarding works** - Git operations use forwarded keys through the SSH chain

## Shared Resources

Resources shared across all containers:

| Path | Purpose |
|------|---------|
| `/srv/fast/code/voidlabs-devtools` | Shared scripts, hooks, templates |
| `~/.claude` | Claude Code settings (synced across containers) |
| `~/.ssh` | SSH keys (forwarded from Mac) |

## Development Tools

- **Cursor** - Connects via SSH Remote extension, then attaches to containers
- **Claude Code** - CLI in terminal, uses shared settings
- **Factory Droid** - Local LLM agent (configured via `bd setup factory`)
- **OpenAI Codex** - API-based agent

## Docker Context (Mac)

The Mac's docker CLI points to the remote host:

```bash
docker context use quasar  # quasar = ssh://chris@docker.voidlabs.local
```

## Creating New Projects

Use the devtools script:

```bash
/srv/fast/code/voidlabs-devtools/scripts/new-project.sh <project-name> <target-dir>
```

This creates `.devcontainer/`, copies `AGENTS.md`, and sets up voidlabs-devtools integration.

## Related

- [[development/project-structure]] - Standard project layout
- [[devops/deployment]] - How projects get deployed
