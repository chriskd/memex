---
title: MX Session Memory vNext
tags:
  - mx
  - memory
  - roadmap
  - dense-signals
  - eval
  - a-mem
created: 2026-01-24T20:18:05.545604+00:00
updated: 2026-01-24T20:52:03.514574+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
semantic_links:
  - path: reference/agent-memory-comparison.md
    score: 0.712
    reason: embedding_similarity
  - path: reference/dense-memory-signals-research.md
    score: 0.67
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-evolution-strategy-parity-refactor.md
    score: 0.632
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-vs-mx-implementation-audit.md
    score: 0.61
    reason: embedding_similarity
  - path: roadmap/a-mem-component-audit-summary.md
    score: 0.811
    reason: bidirectional
---

# MX Session Memory vNext (A-Mem Retcon + Dense Signals + Eval)

## Context
We tried to align mx with A-Mem and LoCoMo parity, but mx is document-centric while A-Mem is built around atomic memory notes. Full parity creates friction and dead code. This roadmap pivots to session-resume memory as the primary goal, while keeping the best A-Mem ideas (enrichment, evolution, metadata) that help that goal.

## Goal
Ship a reliable session-resume memory layer that survives context resets with minimal tokens and measurable improvements.

## Keep / Drop Rubric
Keep when the component directly improves session-resume memory, token efficiency, or observability.
Drop or archive when the component only exists for LoCoMo or A-Mem parity and does not support session-resume memory.

## Keep (likely)
- Metadata enrichment: tags, keywords, descriptions
- Memory evolution (updating stale facts and preferences)
- Timing and progress instrumentation
- Keyword extraction and LLM query refinement (when it helps retrieval)

## Drop or Archive (after replacement is ready)
- LoCoMo-specific adapters and parity eval paths
- A-Mem parity prompts and paper-specific eval defaults
- Any LoCoMo-only fixtures or metrics that do not map to session-resume memory

## Session Memory Contract (summary)
Session memory must capture:
- Decisions and rationale
- Blockers and why
- Preferences and updates
- Next-step / open loops
- Entity facts tied to the user and project

Session memory must avoid:
- Transient chatter
- Redundant copies of raw transcripts
- Stale facts without updates

## Dense Signals Plan
Dense signals are compact, high-value cues injected at session start (100-300 tokens). Use git and session artifacts (branch, staged/stash, build status, last decisions, blockers, next step). This is the primary path for improving session-resume memory.

## Evaluation Plan
Build a session-resume benchmark (synthetic sessions + QA) with metrics: EM/F1, false-positive rate, staleness, token budget. Use this to validate dense signals and memory evolution changes.

## Work Tracking (tickets)
- Roadmap epic: m-ee3d
- Eval framework epic: m-0437
- A-Mem component audit: m-e3de
- Session memory contract + injection template: m-9392
- Dense signals epic: (recreate in this branch if needed)

## Phases
1) Audit A-Mem components and decide keep/drop
2) Define session memory contract and injection template
3) Build session-resume eval harness and record baseline
4) Implement dense signals v1 and measure improvements
5) Archive or remove LoCoMo/A-Mem parity assets after replacements land

## Non-goals
- Achieving full A-Mem parity
- Reproducing LoCoMo scores as a primary objective