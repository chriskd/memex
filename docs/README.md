# Start Here

`mx` is the CLI for Memex knowledge bases: Markdown files with YAML frontmatter, stored in a project KB (`./kb/`) and/or a user KB (`~/.memex/kb/`).

## 60-Second First Run

```bash
# 1) Guided setup (safe to run repeatedly). If no KB is configured, this can create one.
mx onboard --init --yes        # includes a sample entry under inbox/

# 2) Alternatively, initialize directly:
mx init --sample               # project KB: ./kb + ./.kbconfig
# or:
mx init --user --sample        # user KB: ~/.memex/kb

# 3) Confirm it works
mx list --limit=5
mx get @project/inbox/first-task.md   # or @user/... depending on what you initialized
mx search "First Task"
```

For non-interactive environments (agents/CI):

```bash
mx onboard --init --yes
```

## Discoverability Cheatsheet

```bash
mx --help
mx help search
mx schema --compact            # CLI schema for LLM tools
mx doctor                      # deps + install hints
```

## Repo Notes (memex-kb)

- Docs are also stored as KB entries under `kb/` (start with `kb/guides/quick-start.md`).
- Tickets for this repo live in `.tickets/` and are managed with `tk`:
  - `tk list`, `tk show <id>`, `tk add-note <id>`, `tk start <id>`, `tk close <id>`.
