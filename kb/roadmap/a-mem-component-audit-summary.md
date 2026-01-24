---
title: A-Mem Component Audit (Summary)
tags:
  - a-mem
  - audit
  - roadmap
  - eval
created: 2026-01-24T20:51:58.825752+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
git_branch: session-memory-improvements
last_edited_by: chris
semantic_links:
  - path: roadmap/mx-session-memory-vnext.md
    score: 0.811
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-vs-mx-implementation-audit.md
    score: 0.725
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-evaluation-methodology.md
    score: 0.687
    reason: embedding_similarity
  - path: memex/chunking-system-design.md
    score: 0.668
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-parity-analysis.md
    score: 0.645
    reason: embedding_similarity
---

# A-Mem Component Audit (Keep/Drop/Repurpose)

This summarizes the A‑Mem parity audit and maps components to keep/drop/repurpose decisions for the session‑resume vNext plan.

## Code Components

### src/memex/eval/locomo.py
- **What it is**: LoCoMo dataset loader/adapter + heuristic enrichment (tags/keywords/description/context), builds `AdaptedDataset` and QA pairs, and maps LoCoMo categories.
- **Decision**: **Repurpose**
- **Why**: The adapter patterns are useful, but LoCoMo categories don’t match session‑resume memory. Rework into a session‑resume dataset adapter.

### src/memex/eval/runner.py
- **What it is**: End‑to‑end eval harness (temp KB, indexing, A‑Mem linking/evolution hooks, retrieval metrics, LLM query generation, QA prompts, ablations, caching).
- **Decision**: **Keep/Repurpose**
- **Why**: Good scaffolding for a new eval harness. Keep the runner structure, timing/progress, and retrieval metrics (R@K/MRR/nDCG/MAP), but replace LoCoMo‑specific logic.

### src/memex/eval/metrics.py
- **What it is**: LoCoMo QA metrics (F1/ROUGE/BLEU/BERTScore/METEOR/SBERT) with heavy deps.
- **Decision**: **Drop/Archive** (after vNext eval exists)
- **Why**: Not aligned to session‑resume goals; heavy dependencies. Use a simpler metric set for vNext.

### src/memex/cli.py (eval command)
- **What it is**: LoCoMo eval CLI surface + `--amem` defaults.
- **Decision**: **Repurpose**
- **Why**: Keep the CLI entrypoint but retarget to session‑resume eval. Keep `--json`, `--kb-root`, `--ablation` style controls.

### scripts/evolution_ab_test.py
- **Decision**: **Drop/Archive**
- **Why**: Duplicates runner flow; not aligned with new eval targets.

### LLM prompt surface (src/memex/llm.py + eval prompts)
- **Decision**: **Repurpose**
- **Why**: A‑Mem‑style enrichment/evolution prompts still apply, but update for session‑resume contract and dataset.

## KB / Docs / Tests

### Keep (or keep until replaced)
- `tests/test_memory_amem.py` (if still validating session‑memory mode in the branch)
- A‑Mem evolution/enrichment docs that describe current behavior (use as reference while migrating)

### Archive
- Historical parity audits / LoCoMo‑specific docs once vNext is in place

### Cleanup tasks
- Update or archive `a-mem-init` spec to reflect current behavior
- Fix encoding/formatting drift in parity docs (if retained in branch)
- Remove LoCoMo fixtures/tests once vNext eval lands

## Next Steps
- Build session‑resume eval harness (m‑0437)
- Define session memory contract + injection template (m‑9392)
- Replace LoCoMo adapter/metrics with vNext dataset + metrics
- Archive legacy A‑Mem parity assets after vNext is stable

