---
title: A-Mem Test Cases for Agent Evaluation
tags:
  - testing
  - a-mem
  - evaluation
  - agents
created: 2026-01-15T02:05:06.312359+00:00
updated: 2026-01-15T05:42:50.199590+00:00
contributors:
  - chriskd <2326567+chriskd@users.noreply.github.com>
source_project: memex
keywords:
  - test-cases
  - agent-behavior
  - memory-evolution
  - semantic-linking
  - keyword-extraction
  - A-Mem-parity
semantic_links:
  - path: a-mem-parity/a-mem-evaluation-methodology.md
    score: 0.727
    reason: embedding_similarity
  - path: '@project/guides/ai-integration.md'
    score: 0.665
    reason: embedding_similarity
  - path: projects/memex/test-evolution-queue-fix.md
    score: 0.722
    reason: bidirectional
  - path: guides/ai-integration.md
    score: 0.667
    reason: embedding_similarity
  - path: reference/focusgroup-evaluation-mx-cli-discoverability-2026-01.md
    score: 0.609
    reason: embedding_similarity
  - path: memex/chunking-system-design.md
    score: 0.622
    reason: bidirectional
---

# A-Mem Test Cases for Agent Evaluation

This document provides structured test cases that AI agents can walk through to evaluate how well `mx` implements the A-Mem specification (NeurIPS 2025).

## Test Architecture

The A-Mem system has a specific division of labor:

| Component | Responsibility |
|-----------|---------------|
| **LLM Agent** | Keywords extraction, content creation, semantic reasoning at add-time |
| **mx** | Embedding enrichment, bidirectional linking, evolution queue management, LLM-driven evolution |

These test cases evaluate BOTH the agent's correct usage AND mx's automatic behaviors.

---

## Test Suite 1: Entry Creation with A-Mem Strict Mode

### Test 1.1: Strict Mode Enforcement

**Objective**: Verify that amem_strict mode enforces keyword requirements.

**Setup**:
```bash
# Check current strict mode setting
mx config get amem_strict
```

**Test Steps**:
1. Attempt to add an entry WITHOUT keywords:
   ```bash
   mx add --title="Test Entry No Keywords" --tags="test" --content="This is test content about API design."
   ```
2. Expected: Command fails with `AMEMStrictError` explaining the requirement
3. Verify error message includes example of correct usage

**Pass Criteria**: Entry creation is blocked, helpful error displayed.

---

### Test 1.2: Agent Keyword Extraction Quality

**Objective**: Evaluate the agent's ability to extract meaningful keywords from content.

**Scenario Content**:
```
Implementing rate limiting in REST APIs requires careful consideration of 
throttling strategies. Common approaches include token bucket algorithms, 
sliding window counters, and fixed window limits. Each has tradeoffs for 
burst handling and memory consumption.
```

**Expected Keywords** (agent should identify):
- `rate-limiting`
- `throttling`
- `token-bucket`
- `sliding-window`
- `REST-API`
- `burst-handling`

**Test Steps**:
1. Agent analyzes content and proposes keywords
2. Execute:
   ```bash
   mx add --title="Rate Limiting Strategies"      --tags="api,performance"      --keywords="rate-limiting,throttling,token-bucket,sliding-window,REST-API"      --content="[content above]"
   ```
3. Verify entry created with keywords in frontmatter

**Pass Criteria**: 
- Keywords capture core concepts (not generic words)
- Keywords include domain-specific terminology
- Keywords include related concepts not explicitly stated (good agents will add "API-design")

---

### Test 1.3: Keyword Diversity Assessment

**Objective**: Ensure keywords cover multiple semantic dimensions.

**Scenario**: Add 3 entries on related but distinct topics:

**Entry A - "Caching Strategies"**:
```bash
mx add --title="Caching Strategies"   --tags="performance,architecture"   --keywords="caching,TTL,cache-invalidation,Redis,in-memory"   --content="Effective caching requires understanding TTL policies, invalidation strategies..."
```

**Entry B - "Database Query Optimization"**:
```bash
mx add --title="Database Query Optimization"   --tags="performance,database"   --keywords="query-optimization,indexing,explain-plan,N+1,eager-loading"   --content="Optimizing database queries involves proper indexing, avoiding N+1..."
```

**Entry C - "API Performance Monitoring"**:
```bash
mx add --title="API Performance Monitoring"   --tags="performance,observability"   --keywords="latency,p99,metrics,tracing,SLO"   --content="Monitoring API performance requires tracking latency percentiles..."
```

**Pass Criteria**:
- Each entry has distinct keyword sets
- Related concepts share some overlap (all are "performance")
- Domain terminology is specific (not generic like "fast", "good")

---

## Test Suite 2: Semantic Linking (Automatic)

### Test 2.1: Bidirectional Link Creation

**Objective**: Verify mx creates semantic links between related entries.

**Setup**: Complete Test 1.3 (create 3 performance-related entries)

**Test Steps**:
1. Check links on newest entry:
   ```bash
   mx get a-mem-parity/api-performance-monitoring.md --metadata
   ```
2. Verify `semantic_links` field contains:
   - Links to related entries with `score > 0.6`
   - `reason: "embedding_similarity"` for forward links

3. Check backlinks on older entry:
   ```bash
   mx get a-mem-parity/caching-strategies.md --metadata
   ```
4. Verify it has a backlink with `reason: "bidirectional"`

**Pass Criteria**:
- New entries automatically link to similar existing entries
- Backlinks are created on neighbor entries
- Similarity scores reflect actual semantic relatedness

---

### Test 2.2: Cross-Topic Non-Linking

**Objective**: Verify unrelated entries do NOT get linked.

**Test Steps**:
1. Add a completely unrelated entry:
   ```bash
   mx add --title="Sourdough Bread Recipe"      --tags="cooking,recipe"      --keywords="sourdough,fermentation,bread,starter,gluten"      --content="Making sourdough requires a healthy starter culture..."
   ```
2. Check its semantic links:
   ```bash
   mx get a-mem-parity/sourdough-bread-recipe.md --metadata
   ```

**Pass Criteria**:
- No semantic links to performance/API entries (score threshold prevents false links)
- If any links exist, scores should be very low (< 0.5)

---

### Test 2.3: Link Provenance Tracking

**Objective**: Verify link reasons are tracked correctly.

**Test Steps**:
1. View links with full detail:
   ```bash
   mx get a-mem-parity/caching-strategies.md
   ```
2. Examine `semantic_links` array

**Expected Structure**:
```yaml
semantic_links:
  - path: a-mem-parity/database-query-optimization.md
    score: 0.72
    reason: embedding_similarity
  - path: a-mem-parity/api-performance-monitoring.md
    score: 0.68
    reason: bidirectional
```

**Pass Criteria**: Each link has path, score, and reason tracked.

---

## Test Suite 3: Memory Evolution (LLM-Driven)

### Test 3.1: Evolution Queue Population

**Objective**: Verify entries are queued for evolution.

**Test Steps**:
1. After adding entries, check queue status:
   ```bash
   mx evolve --status
   ```
2. Verify queue contains items with:
   - `new_entry`: path to newly added entry
   - `neighbor`: paths to related entries
   - `score`: similarity score that triggered queueing
   - `queued_at`: timestamp

**Pass Criteria**: Related neighbors are queued for evolution.

---

### Test 3.2: Evolution Execution

**Objective**: Verify LLM-driven evolution updates neighbor keywords.

**Prerequisites**:
- `OPENROUTER_API_KEY` set
- Evolution queue has pending items

**Test Steps**:
1. Note current keywords on a neighbor entry:
   ```bash
   mx get a-mem-parity/caching-strategies.md --metadata | grep keywords
   ```
2. Run evolution:
   ```bash
   mx evolve
   ```
3. Check updated keywords:
   ```bash
   mx get a-mem-parity/caching-strategies.md --metadata | grep keywords
   ```

**Expected Behavior**:
- LLM analyzes relationship between new entry and neighbor
- Suggests new keywords to add to neighbor
- Keywords are added (duplicates filtered)
- Entry is re-indexed with enriched embeddings

**Pass Criteria**:
- Neighbor entry has new keywords added
- Keywords are semantically relevant to the connection
- No duplicate keywords introduced

---

### Test 3.3: Evolution Cascading Effect

**Objective**: Verify evolved entries improve future search relevance.

**Test Steps**:
1. Before evolution, search:
   ```bash
   mx search "API throttling strategies"
   ```
2. Note which entries appear and their ranking

3. Run evolution (if pending):
   ```bash
   mx evolve
   ```

4. Search again with same query:
   ```bash
   mx search "API throttling strategies"
   ```

**Pass Criteria**:
- After evolution, related entries rank higher
- Keywords from evolution improve search matches

---

## Test Suite 4: Search Quality

### Test 4.1: Hybrid Search (Keyword + Semantic)

**Objective**: Verify search combines keyword matching with semantic similarity.

**Test Steps**:
1. Search by exact keyword:
   ```bash
   mx search "token-bucket"
   ```
2. Search by related concept:
   ```bash
   mx search "request rate control"
   ```

**Pass Criteria**:
- Exact keyword search returns entry with that keyword
- Semantic search returns conceptually related entries even without keyword match

---

### Test 4.2: Keyword-Enriched Embeddings

**Objective**: Verify keywords influence semantic search results.

**Test Steps**:
1. Search for a keyword that's in metadata but not in content body:
   ```bash
   mx search "N+1"  # If "N+1" is keyword but not in body
   ```

**Pass Criteria**: Entry is found because embeddings include keywords.

---

### Test 4.3: Tag-Based Filtering

**Objective**: Verify tag filtering works with search.

**Test Steps**:
```bash
mx search "optimization" --tags=database
```

**Pass Criteria**: Only entries with matching tag AND query relevance returned.

---

## Test Suite 5: A-Mem Parity Validation

### Test 5.1: Memory Structure Completeness

**Objective**: Verify entries have all A-Mem required fields.

**A-Mem Fields** (from spec):
- `core_content` (c_i) â content body â
- `timestamp` (t_i) â created/updated â
- `tags` (T_i) â tags field â
- `keywords` (K_i) â keywords field â
- `context` (X_i) â description field (partial)
- `embedding` (e_i) â ChromaDB indexed â
- `links` (L_i) â semantic_links â

**Test Steps**:
```bash
mx get a-mem-parity/rate-limiting-strategies.md
```

**Pass Criteria**: All required fields present and populated.

---

### Test 5.2: Embedding Enrichment Verification

**Objective**: Confirm embeddings include keywords+tags, not just content.

**Test Steps**:
1. Create two entries with identical content but different keywords:

   **Entry A**:
   ```bash
   mx add --title="Generic Content A"      --tags="test"      --keywords="machine-learning,neural-networks"      --content="A system that processes data and produces outputs."
   ```
   
   **Entry B**:
   ```bash
   mx add --title="Generic Content B"      --tags="test"      --keywords="plumbing,pipe-fitting"      --content="A system that processes data and produces outputs."
   ```

2. Search for ML concepts:
   ```bash
   mx search "deep learning neural network"
   ```

**Pass Criteria**: Entry A ranks higher than Entry B due to keyword enrichment.

---

### Test 5.3: Link Quality Assessment

**Objective**: Evaluate if semantic links reflect meaningful relationships.

**Test Steps**:
1. Add entries with known relationships:
   - Parent concept: "Microservices Architecture"
   - Child concept: "Service Discovery in Microservices"
   - Related concept: "API Gateway Patterns"
   - Unrelated: "Plant Care Guide"

2. Examine links on "Service Discovery" entry
3. Score link quality:
   - Parent should be linked (high score)
   - Related should be linked (medium score)
   - Unrelated should NOT be linked (below threshold)

**Pass Criteria**: Links match expected conceptual relationships.

---

## Test Suite 6: Agent Workflow Integration

### Test 6.1: Full Agent Add Workflow

**Objective**: Test complete agent workflow for adding knowledge.

**Scenario**: Agent discovers useful information during task and adds to KB.

**Agent Script**:
```
1. Analyze content to extract:
   - Appropriate title
   - Relevant tags (2-4)
   - Key concepts as keywords (3-6)
   - Clean content
   
2. Execute:
   mx add --title="..." --tags="..." --keywords="..." --content="..."
   
3. Verify entry created:
   mx get <path>
   
4. Check semantic links formed:
   mx get <path> --metadata
```

**Pass Criteria**:
- Agent provides all required fields
- Entry integrates into existing knowledge graph
- Semantic links connect to related entries

---

### Test 6.2: Agent Search and Retrieval

**Objective**: Test agent's ability to find and use KB knowledge.

**Scenario**: Agent needs information about a topic.

**Agent Script**:
```
1. Search KB:
   mx search "topic query"
   
2. Read relevant entry:
   mx get <best-match-path>
   
3. Use information in response to user
   
4. Optionally add new insights:
   mx add --title="..." --keywords="..." --content="new insight + citation"
```

**Pass Criteria**:
- Search returns relevant results
- Agent can parse and use entry content
- New knowledge links back to source

---

### Test 6.3: Evolution Awareness

**Objective**: Agent understands evolution is queued, not immediate.

**Test Steps**:
1. Agent adds entry
2. Agent checks evolution status:
   ```bash
   mx evolve --status
   ```
3. Agent understands neighbors will be updated asynchronously
4. Agent can trigger evolution if needed:
   ```bash
   mx evolve
   ```

**Pass Criteria**: Agent doesn't expect immediate neighbor updates.

---

## Scoring Rubric

### Agent Behavior Scores (1-5)

| Criterion | 1 (Poor) | 3 (Acceptable) | 5 (Excellent) |
|-----------|----------|----------------|---------------|
| Keyword Quality | Generic words | Mix of generic and specific | Domain-specific, concept-rich |
| Keyword Coverage | Missing key concepts | Covers main points | Includes related/inferred concepts |
| Tag Appropriateness | Wrong categories | Correct but broad | Precise and hierarchical |
| Content Quality | Unclear, verbose | Clear, somewhat structured | Well-organized, referenceable |

### mx System Scores (1-5)

| Criterion | 1 (Poor) | 3 (Acceptable) | 5 (Excellent) |
|-----------|----------|----------------|---------------|
| Link Accuracy | Many false positives | Mostly correct | Precise, meaningful links |
| Evolution Quality | Keywords don't help | Some improvement | Significant relevance boost |
| Search Relevance | Unrelated results | Correct top result | Well-ranked by relevance |
| Strict Mode UX | Confusing errors | Clear errors | Helpful with examples |

---

## Cleanup Commands

After testing, remove test entries:
```bash
# List test entries
mx list --tags=test

# Manual cleanup (entries in testing category)
# Note: No bulk delete - remove files manually if needed
```

---

## Notes for Test Execution

1. **Run in isolated KB**: Consider using `MEMEX_KB_ROOT` to point to test KB
2. **Check config first**: `mx config show` to understand current settings
3. **Evolution requires API key**: Set `OPENROUTER_API_KEY` for evolution tests
4. **Non-blocking design**: Evolution is async - don't expect immediate updates
5. **Scoring is subjective**: Use rubric as guide, not strict grading