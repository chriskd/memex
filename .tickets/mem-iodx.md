---
id: mem-iodx
status: open
deps: []
links: []
created: 2026-02-08T08:00:19Z
type: feature
priority: 2
assignee: chriskd
---
# mx doctor: fix frontmatter timestamps from filesystem metadata

## Summary

Add support in `mx doctor` to detect and optionally correct entry frontmatter timestamps (`created`, `updated`) using filesystem metadata (best-effort).

Motivation: KBs often accumulate missing or incorrect timestamps (manual edits, imports, renames). That breaks recency-based workflows (`mx whats-new`, “recent entries” status display) and makes it harder for agents to trust timelines.

## Requirements / Constraints

- **Safety first**: default is report-only. Writing requires an explicit flag.
- **Best-effort creation time**:
  - Prefer filesystem birthtime when available (macOS / BSD `st_birthtime`).
  - Otherwise use `ctime` as a fallback (note: on Linux it is change-time, not true creation).
- **Updated time** should use filesystem `mtime`.
- Only modify entries that are missing timestamps or have invalid/non-parseable timestamps unless `--force` is provided.
- Must support both human output and `--json`.

## Proposed CLI UX

- Report: `mx doctor --timestamps`
- Apply: `mx doctor --timestamps --fix`
- Safety/controls:
  - `--dry-run` (compute and show changes without writing)
  - `--force` (overwrite even valid timestamps)
  - `--scope` / `--limit` consistent with other commands where applicable
  - `--json` for per-file before/after + source (birthtime|ctime|mtime)

## Acceptance Criteria

- [ ] `mx doctor --timestamps` reports entries with missing/invalid `created` and/or `updated`.
- [ ] `mx doctor --timestamps --fix` updates YAML frontmatter in-place using best-effort filesystem times (created from birthtime/ctime, updated from mtime).
- [ ] Does not modify entries with valid timestamps unless `--force` is used.
- [ ] Provides `--dry-run` and a clear summary (checked/changed/skipped); non-zero exit only on real errors.
- [ ] `--json` includes per-file before/after timestamps and which source was used for each field.

## Notes

**2026-02-08T08:01:25Z**

Ticket body corrected (initial create command suffered shell backtick substitution).
