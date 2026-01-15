---
title: A-Mem Evaluation Methodology
tags:
  - a-mem
  - testing
  - evaluation
created: 2026-01-14T23:36:01.305747+00:00
updated: 2026-01-15T03:22:55.050600+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
semantic_links:
  - path: a-mem-parity/a-mem-parity-analysis.md
    score: 0.735
    reason: embedding_similarity
  - path: a-mem-parity/a-mem-test-cases-for-agent-evaluation.md
    score: 0.727
    reason: bidirectional
---

# A-Mem Evaluation Methodology

This document describes the testing methodology for evaluating Memex's A-Mem implementation effectiveness.

## Background: A-Mem Paper Evaluation

The original A-Mem paper (NeurIPS 2025) evaluated using:
- **Dataset**: LoCoMo (7,512 QA pairs across long conversations, ~9K tokens, 35 sessions)
- **Question types**: Single-hop, Multi-hop, Temporal reasoning, Open-domain, Adversarial
- **Metrics**: F1 score, BLEU-1, ROUGE-L, ROUGE-2, METEOR, SBERT Similarity
- **Key result**: A-Mem achieved F1 of 45.85% on Multi-Hop vs MemGPT's 25.52%
- **Token efficiency**: 2,520 tokens vs 16,977 baseline

## Our Context

Memex is a CLI-based knowledge base, not a conversational agent. Our A-Mem features are:
1. **Keywords enriching embeddings**: Content + keywords + tags concatenated before embedding
2. **Semantic linking (bidirectional)**: Auto-created forward and backward links based on embedding similarity
3. **Graph-aware search**: `--include-neighbors` flag traverses semantic links

## Evaluation Approach

### 1. Keyword Embedding Effectiveness

**Goal**: Verify that keywords improve search relevance.

**Method**:
- Create test entries with specific keywords
- Search using keyword terms NOT in the content
- Compare results with/without keyword enrichment

**Metrics**:
- **Recall@K**: Does the correct entry appear in top-K results?
- **Rank improvement**: How much higher does it rank with keywords?
- **Precision**: Are top results actually relevant?

**Test Cases**:
```
Entry: "Guide to fast Python execution"
Keywords: ["optimization", "performance", "cython", "numba"]
Query: "python optimization" -> Should find this entry
Query: "cython" -> Should find this entry (keyword match)
```

### 2. Semantic Link Quality

**Goal**: Verify that auto-created semantic links are meaningful.

**Method**:
- Create entries with known semantic relationships
- Let auto-linking run
- Verify correct links are created

**Metrics**:
- **Link precision**: What % of auto-links are actually meaningful?
- **Link recall**: What % of meaningful relationships are captured?
- **Bidirectional integrity**: Are backlinks always created?

**Test Cases**:
```
Entry A: "Python Type Hints Guide" (tags: python, typing)
Entry B: "TypeScript Type System" (tags: typescript, typing)
Entry C: "Pizza Recipes" (tags: cooking, food)

Expected:
- A <-> B: Should be linked (shared topic: typing)
- A <-> C: Should NOT be linked (unrelated)
```

### 3. Graph Traversal Effectiveness

**Goal**: Verify that `--include-neighbors` finds otherwise-missed results.

**Method**:
- Create chain of related entries (A -> B -> C)
- Search for term only in entry C
- Compare results with/without neighbor expansion

**Metrics**:
- **Coverage gain**: How many additional relevant results found?
- **Noise ratio**: What % of neighbors are actually relevant?
- **Depth effectiveness**: Is depth=2 better than depth=1?

**Test Cases**:
```
Chain: "ML Basics" -> "Neural Networks" -> "Backpropagation"
Query: "gradient descent" (in Backpropagation only)
Without neighbors: Finds Backpropagation
With neighbors: Finds Backpropagation + Neural Networks + ML Basics
```

## Test Implementation

### Fixture Structure

```
tests/
  fixtures/
    amem_evaluation/
      keyword_test_entries.yaml    # Entries for keyword testing
      linking_test_entries.yaml    # Entries for link testing
      graph_test_entries.yaml      # Entries for graph traversal
      ground_truth.yaml            # Expected results
```

### Test Categories

1. **Unit tests** (`test_amem_evaluation.py`):
   - Keyword embedding construction
   - Link creation logic
   - Graph traversal mechanics

2. **Integration tests** (CLI-based):
   - Full add -> search -> verify flow
   - With/without feature flags

3. **Quality benchmarks** (extending `evaluation.py`):
   - Add A-Mem-specific test queries
   - Track improvement over baseline

## Metrics We Can Measure

### Search Quality

| Metric | Description | Target |
|--------|-------------|--------|
| **MRR** (Mean Reciprocal Rank) | Average of 1/rank for correct results | > 0.7 |
| **Recall@3** | % of queries where correct result in top 3 | > 80% |
| **Recall@10** | % of queries where correct result in top 10 | > 95% |

### Link Quality

| Metric | Description | Target |
|--------|-------------|--------|
| **Link Precision** | Meaningful links / Total auto-links | > 80% |
| **Bidirectional Rate** | Entries with backlinks / Entries with forward links | 100% |
| **Cluster Accuracy** | Entries in same topic linked together | > 70% |

### Graph Search

| Metric | Description | Target |
|--------|-------------|--------|
| **Coverage Gain** | Additional relevant results via neighbors | > 20% |
| **Noise Rate** | Irrelevant neighbors / Total neighbors | < 30% |

## Running Evaluations

```bash
# Run A-Mem specific tests
uv run pytest tests/test_amem_evaluation.py -v

# Run quality benchmark with A-Mem features
mx quality --verbose

# Manual verification of specific scenarios
mx search "query" --include-neighbors --json | jq '.results'
```

## Comparison with Baseline

To measure A-Mem effectiveness, compare:

| Scenario | Baseline | With A-Mem |
|----------|----------|------------|
| Keyword-only query | Semantic fallback | Direct keyword match |
| Multi-hop reasoning | Miss related content | Find via graph |
| Concept discovery | Only exact matches | Related concepts |

## Future Extensions

1. **Token efficiency tracking**: Measure tokens used by semantic links vs benefit
2. **Temporal evaluation**: Test recency-weighted retrieval
3. **Multi-hop QA pairs**: Create LoCoMo-style evaluation dataset for Memex
4. **A/B testing framework**: Compare search quality with features on/off