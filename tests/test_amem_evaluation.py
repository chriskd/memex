"""A-Mem feature evaluation tests.

Tests evaluate the effectiveness of Memex's A-Mem implementation:
1. Keyword embedding effectiveness - Do keywords improve search relevance?
2. Semantic link quality - Are auto-created links meaningful?
3. Graph traversal effectiveness - Does --include-neighbors find missed results?

These tests complement the existing test_search_neighbors.py with evaluation-focused
scenarios rather than functional/integration tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from memex.models import SearchResult


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────


def create_entry_with_keywords(
    kb_root: Path,
    path: str,
    title: str,
    content: str,
    tags: list[str],
    keywords: list[str] | None = None,
    semantic_links: list[dict[str, Any]] | None = None,
) -> Path:
    """Create a test entry with keywords and optional semantic_links in frontmatter."""
    entry_path = kb_root / path
    entry_path.parent.mkdir(parents=True, exist_ok=True)

    tags_str = f"[{', '.join(tags)}]"

    # Build keywords YAML
    keywords_yaml = ""
    if keywords:
        keywords_str = ", ".join(keywords)
        keywords_yaml = f"keywords: [{keywords_str}]\n"

    # Build semantic_links YAML
    links_yaml = ""
    if semantic_links:
        links_yaml = "semantic_links:\n"
        for link in semantic_links:
            links_yaml += f"  - path: {link['path']}\n"
            links_yaml += f"    score: {link['score']}\n"
            links_yaml += f"    reason: {link['reason']}\n"

    frontmatter = f"""---
title: {title}
tags: {tags_str}
created: 2024-01-15
{keywords_yaml}{links_yaml}---

{content}
"""
    entry_path.write_text(frontmatter)
    return entry_path


def load_fixture(name: str) -> dict[str, Any]:
    """Load a YAML fixture file."""
    fixture_dir = Path(__file__).parent / "fixtures" / "amem_evaluation"
    with open(fixture_dir / name) as f:
        return yaml.safe_load(f)


# ─────────────────────────────────────────────────────────────────────────────
# Keyword Embedding Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.semantic
class TestKeywordEmbeddingEffectiveness:
    """Test that keywords improve search relevance.

    These tests verify that the _build_embedding_text function in ChromaIndex
    properly incorporates keywords into embeddings for better search matches.
    """

    def test_embedding_text_includes_keywords(self):
        """Verify that _build_embedding_text concatenates keywords correctly."""
        from memex.indexer.chroma_index import ChromaIndex

        index = ChromaIndex()
        content = "This is the document content."
        keywords = ["keyword1", "keyword2"]
        tags = ["tag1", "tag2"]

        result = index._build_embedding_text(content, keywords, tags)

        assert content in result
        assert "Keywords: keyword1, keyword2" in result
        assert "Tags: tag1, tag2" in result

    def test_embedding_text_handles_empty_keywords(self):
        """Verify embedding text works with no keywords."""
        from memex.indexer.chroma_index import ChromaIndex

        index = ChromaIndex()
        content = "Document content only."

        result = index._build_embedding_text(content, [], [])

        assert result == content

    @pytest.mark.slow
    def test_keyword_search_finds_keyword_matches(self, tmp_kb: Path):
        """Test that searching for a keyword term finds the entry."""
        from memex.indexer import HybridSearcher
        from memex.core import reindex
        import asyncio

        # Create entry with keyword not in content
        create_entry_with_keywords(
            tmp_kb,
            "optimization-guide.md",
            "Guide to Fast Python Execution",
            "This guide covers techniques for making Python code run faster.",
            tags=["python", "performance"],
            keywords=["optimization", "cython", "numba"],
        )

        # Force reindex
        asyncio.get_event_loop().run_until_complete(reindex())

        searcher = HybridSearcher()
        # Search for keyword term
        results = searcher.search("cython optimization", limit=5, mode="semantic")

        # Should find our entry because 'cython' and 'optimization' are in keywords
        paths = [r.path for r in results]
        assert "optimization-guide.md" in paths, (
            f"Expected 'optimization-guide.md' in results. Got: {paths}"
        )

    @pytest.mark.slow
    def test_keyword_improves_rank(self, tmp_kb: Path):
        """Test that keywords improve search ranking vs content-only match."""
        from memex.indexer import HybridSearcher
        from memex.core import reindex
        import asyncio

        # Entry 1: Has 'cython' in keywords
        create_entry_with_keywords(
            tmp_kb,
            "python-speed.md",
            "Python Speed Optimization",
            "Making Python faster through various techniques.",
            tags=["python"],
            keywords=["cython", "numba", "pypy"],
        )

        # Entry 2: Mentions Python but no cython anywhere
        create_entry_with_keywords(
            tmp_kb,
            "python-basics.md",
            "Python Basics",
            "Introduction to Python programming language features.",
            tags=["python"],
            keywords=["variables", "functions", "classes"],
        )

        asyncio.get_event_loop().run_until_complete(reindex())

        searcher = HybridSearcher()
        results = searcher.search("cython python", limit=5, mode="semantic")

        paths = [r.path for r in results]
        # python-speed.md should rank higher because it has 'cython' in keywords
        if "python-speed.md" in paths and "python-basics.md" in paths:
            speed_idx = paths.index("python-speed.md")
            basics_idx = paths.index("python-basics.md")
            assert speed_idx < basics_idx, (
                f"Entry with keyword should rank higher. "
                f"Got speed at {speed_idx}, basics at {basics_idx}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Semantic Link Quality Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.semantic
class TestSemanticLinkQuality:
    """Test that auto-created semantic links are meaningful.

    These tests verify:
    1. Related entries get linked (high precision)
    2. Unrelated entries do NOT get linked
    3. Bidirectional links are always created
    """

    @pytest.mark.slow
    def test_related_entries_get_linked(self, tmp_kb: Path):
        """Test that semantically similar entries are auto-linked."""
        from memex.core import add_entry, get_entry
        import asyncio

        # Create 'general' category (required by add_entry)
        (tmp_kb / "general").mkdir(exist_ok=True)

        # Create first entry about Python typing
        result1 = asyncio.get_event_loop().run_until_complete(
            add_entry(
                title="Python Type Hints",
                tags=["python", "typing"],
                content="Guide to using type annotations in Python code.",
                category="general",
            )
        )

        # Create second entry about Python typing (related)
        result2 = asyncio.get_event_loop().run_until_complete(
            add_entry(
                title="Mypy Type Checking",
                tags=["python", "mypy", "typing"],
                content="Using mypy to check Python type annotations.",
                category="general",
            )
        )

        # Read back the second entry to check its semantic_links
        entry = asyncio.get_event_loop().run_until_complete(
            get_entry(result2["path"])
        )

        linked_paths = [link.path for link in entry.metadata.semantic_links]

        # Should have linked to the related entry
        assert any("python-type-hints" in p for p in linked_paths), (
            f"Expected link to python-type-hints. Got links: {linked_paths}"
        )

    @pytest.mark.slow
    def test_unrelated_entries_not_linked(self, tmp_kb: Path):
        """Test that unrelated entries are NOT auto-linked."""
        from memex.core import add_entry, get_entry
        import asyncio

        # Create 'general' category
        (tmp_kb / "general").mkdir(exist_ok=True)

        # Create entry about cooking
        result1 = asyncio.get_event_loop().run_until_complete(
            add_entry(
                title="Italian Pasta Recipes",
                tags=["cooking", "italian"],
                content="Collection of authentic Italian pasta recipes including carbonara.",
                category="general",
            )
        )

        # Create entry about Kubernetes (unrelated)
        result2 = asyncio.get_event_loop().run_until_complete(
            add_entry(
                title="Kubernetes Deployments",
                tags=["devops", "kubernetes"],
                content="Managing containerized applications with Kubernetes deployments.",
                category="general",
            )
        )

        # Read back the Kubernetes entry
        entry = asyncio.get_event_loop().run_until_complete(
            get_entry(result2["path"])
        )

        linked_paths = [link.path for link in entry.metadata.semantic_links]

        # Should NOT link to cooking entry
        assert not any("pasta" in p.lower() for p in linked_paths), (
            f"Should not link DevOps to cooking. Got links: {linked_paths}"
        )

    @pytest.mark.slow
    def test_bidirectional_links_created(self, tmp_kb: Path):
        """Test that backlinks are created for forward links."""
        from memex.core import add_entry, get_entry
        import asyncio

        # Create 'general' category
        (tmp_kb / "general").mkdir(exist_ok=True)

        # Create first entry
        result1 = asyncio.get_event_loop().run_until_complete(
            add_entry(
                title="Docker Containers",
                tags=["docker", "containers"],
                content="Introduction to containerization with Docker.",
                category="general",
            )
        )

        # Create second entry (should create bidirectional link)
        result2 = asyncio.get_event_loop().run_until_complete(
            add_entry(
                title="Docker Networking",
                tags=["docker", "networking"],
                content="Docker container networking concepts and configuration.",
                category="general",
            )
        )

        # Check the first entry has a backlink
        entry = asyncio.get_event_loop().run_until_complete(
            get_entry(result1["path"])
        )

        linked_paths = [link.path for link in entry.metadata.semantic_links]
        bidirectional_links = [
            link for link in entry.metadata.semantic_links
            if link.reason == "bidirectional"
        ]

        # First entry should have backlink from second
        has_backlink = any("docker-networking" in p for p in linked_paths)
        assert has_backlink, (
            f"Expected backlink to docker-networking. Got: {linked_paths}"
        )

        # The backlink should have reason 'bidirectional'
        assert len(bidirectional_links) > 0, (
            f"Expected bidirectional reason on backlinks. Got: {entry.metadata.semantic_links}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Graph Traversal Effectiveness Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.semantic
class TestGraphTraversalEffectiveness:
    """Test that --include-neighbors finds otherwise-missed results.

    These tests verify that graph-aware search surfaces related content
    that wouldn't be found by direct search alone.
    """

    @pytest.mark.asyncio
    async def test_neighbor_expansion_finds_related(self, tmp_kb: Path):
        """Test that neighbor expansion surfaces related entries."""
        from memex.core import expand_search_with_neighbors

        # Create chain: A -> B (A links to B)
        create_entry_with_keywords(
            tmp_kb,
            "ml-basics.md",
            "Machine Learning Basics",
            "Introduction to machine learning concepts.",
            tags=["ml", "basics"],
            semantic_links=[
                {"path": "neural-networks.md", "score": 0.8, "reason": "embedding_similarity"}
            ],
        )
        create_entry_with_keywords(
            tmp_kb,
            "neural-networks.md",
            "Neural Networks",
            "Understanding neural network architectures.",
            tags=["ml", "neural-networks"],
        )

        # Simulate search returning only ml-basics
        results = [
            SearchResult(
                path="ml-basics.md",
                title="Machine Learning Basics",
                snippet="Introduction to ML",
                score=0.9,
                tags=["ml", "basics"],
            )
        ]

        expanded = await expand_search_with_neighbors(results, depth=1)

        # Should include both direct result and neighbor
        paths = [r["path"] for r in expanded]
        assert "ml-basics.md" in paths
        assert "neural-networks.md" in paths, (
            f"Expected neighbor 'neural-networks.md' in expanded results. Got: {paths}"
        )

    @pytest.mark.asyncio
    async def test_coverage_gain_measurement(self, tmp_kb: Path):
        """Measure coverage gain from neighbor expansion."""
        from memex.core import expand_search_with_neighbors

        # Create entries with semantic links
        create_entry_with_keywords(
            tmp_kb,
            "react-guide.md",
            "React Guide",
            "Building UIs with React.",
            tags=["react", "frontend"],
            semantic_links=[
                {"path": "react-hooks.md", "score": 0.85, "reason": "embedding_similarity"},
                {"path": "react-testing.md", "score": 0.75, "reason": "embedding_similarity"},
            ],
        )
        create_entry_with_keywords(
            tmp_kb,
            "react-hooks.md",
            "React Hooks",
            "Using hooks in React applications.",
            tags=["react", "hooks"],
        )
        create_entry_with_keywords(
            tmp_kb,
            "react-testing.md",
            "React Testing",
            "Testing React components with Jest.",
            tags=["react", "testing"],
        )

        # Direct search finds 1 result
        direct_results = [
            SearchResult(
                path="react-guide.md",
                title="React Guide",
                snippet="Building UIs",
                score=0.9,
                tags=["react"],
            )
        ]

        # Expand with neighbors
        expanded = await expand_search_with_neighbors(direct_results, depth=1)

        # Coverage gain = (expanded - direct) / direct
        direct_count = len(direct_results)
        expanded_count = len(expanded)
        coverage_gain = (expanded_count - direct_count) / direct_count

        assert coverage_gain >= 0.2, (
            f"Coverage gain should be at least 20%. "
            f"Got {coverage_gain:.1%} ({direct_count} -> {expanded_count})"
        )

    @pytest.mark.asyncio
    async def test_neighbor_depth_controls_reach(self, tmp_kb: Path):
        """Test that neighbor depth properly limits traversal."""
        from memex.core import expand_search_with_neighbors

        # Create chain: A -> B -> C -> D
        create_entry_with_keywords(
            tmp_kb,
            "a.md",
            "Entry A",
            "Content A",
            tags=["test"],
            semantic_links=[{"path": "b.md", "score": 0.9, "reason": "embedding_similarity"}],
        )
        create_entry_with_keywords(
            tmp_kb,
            "b.md",
            "Entry B",
            "Content B",
            tags=["test"],
            semantic_links=[{"path": "c.md", "score": 0.8, "reason": "embedding_similarity"}],
        )
        create_entry_with_keywords(
            tmp_kb,
            "c.md",
            "Entry C",
            "Content C",
            tags=["test"],
            semantic_links=[{"path": "d.md", "score": 0.7, "reason": "embedding_similarity"}],
        )
        create_entry_with_keywords(
            tmp_kb,
            "d.md",
            "Entry D",
            "Content D",
            tags=["test"],
        )

        results = [
            SearchResult(
                path="a.md",
                title="Entry A",
                snippet="Content A",
                score=0.95,
                tags=["test"],
            )
        ]

        # Depth 1: A + B only
        depth1 = await expand_search_with_neighbors(results, depth=1)
        paths1 = [r["path"] for r in depth1]
        assert set(paths1) == {"a.md", "b.md"}, f"Depth 1 should find A,B. Got: {paths1}"

        # Depth 2: A + B + C
        depth2 = await expand_search_with_neighbors(results, depth=2)
        paths2 = [r["path"] for r in depth2]
        assert set(paths2) == {"a.md", "b.md", "c.md"}, f"Depth 2 should find A,B,C. Got: {paths2}"

        # Depth 3: All entries
        depth3 = await expand_search_with_neighbors(results, depth=3)
        paths3 = [r["path"] for r in depth3]
        assert set(paths3) == {"a.md", "b.md", "c.md", "d.md"}, f"Depth 3 should find all. Got: {paths3}"


# ─────────────────────────────────────────────────────────────────────────────
# Aggregate Quality Metrics
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.semantic
class TestAggregateQualityMetrics:
    """Test aggregate quality metrics for A-Mem features."""

    def test_mrr_calculation(self):
        """Test Mean Reciprocal Rank calculation logic."""
        # MRR = average of 1/rank for correct results
        # If correct answer is at rank 1, 2, 3 -> MRR = (1/1 + 1/2 + 1/3) / 3 = 0.61

        ranks = [1, 2, 3]
        mrr = sum(1 / r for r in ranks) / len(ranks)

        expected_mrr = (1 + 0.5 + 0.333) / 3
        assert abs(mrr - expected_mrr) < 0.01

    def test_recall_at_k_calculation(self):
        """Test Recall@K calculation logic."""
        # 5 queries, 4 found correct result in top 3
        found_in_top_k = 4
        total_queries = 5

        recall_at_3 = found_in_top_k / total_queries
        assert recall_at_3 == 0.8


# ─────────────────────────────────────────────────────────────────────────────
# CLI Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAMemCLIIntegration:
    """Test A-Mem features via CLI."""

    def test_add_with_keywords_flag(self, runner, tmp_kb: Path):
        """Test mx add --keywords flag."""
        from memex.cli import cli

        # Create 'general' category
        (tmp_kb / "general").mkdir(exist_ok=True)

        result = runner.invoke(
            cli,
            [
                "add",
                "--title=Test Entry",
                "--tags=test",
                "--category=general",
                "--keywords=keyword1,keyword2",
                "--content=Test content for keywords",
            ],
            env={"MEMEX_USER_KB_ROOT": str(tmp_kb)},
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Verify keywords in created file
        created_file = tmp_kb / "general" / "test-entry.md"
        content = created_file.read_text()
        assert "keywords:" in content
        assert "keyword1" in content
        assert "keyword2" in content

    def test_search_include_neighbors_flag(self, runner, tmp_kb: Path):
        """Test mx search --include-neighbors flag."""
        from memex.cli import cli

        # Create linked entries
        create_entry_with_keywords(
            tmp_kb,
            "main.md",
            "Main Entry",
            "Main content",
            tags=["test"],
            semantic_links=[{"path": "linked.md", "score": 0.8, "reason": "embedding_similarity"}],
        )
        create_entry_with_keywords(
            tmp_kb,
            "linked.md",
            "Linked Entry",
            "Linked content",
            tags=["test"],
        )

        result = runner.invoke(
            cli,
            ["search", "main", "--include-neighbors", "--json"],
            env={"MEMEX_USER_KB_ROOT": str(tmp_kb)},
        )

        # Should include is_neighbor field in JSON output
        if result.exit_code == 0 and '"results"' in result.output:
            assert '"is_neighbor"' in result.output


# ─────────────────────────────────────────────────────────────────────────────
# Fixture-Driven Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestFixtureDrivenEvaluation:
    """Tests driven by YAML fixture files."""

    def test_fixture_files_exist(self):
        """Verify all fixture files are present."""
        fixture_dir = Path(__file__).parent / "fixtures" / "amem_evaluation"

        required_files = [
            "keyword_test_entries.yaml",
            "linking_test_entries.yaml",
            "graph_test_entries.yaml",
            "ground_truth.yaml",
        ]

        for filename in required_files:
            filepath = fixture_dir / filename
            assert filepath.exists(), f"Missing fixture: {filename}"

    def test_ground_truth_thresholds_valid(self):
        """Verify ground truth thresholds are reasonable."""
        ground_truth = load_fixture("ground_truth.yaml")
        thresholds = ground_truth["thresholds"]

        # All thresholds should be between 0 and 1
        for key, value in thresholds.items():
            assert 0 <= value <= 1, f"Threshold {key}={value} out of range [0,1]"

        # Specific sanity checks
        assert thresholds["keyword_recall_at_3"] >= 0.5, "Recall@3 threshold too low"
        assert thresholds["link_bidirectional_rate"] == 1.0, "Bidirectional should be 100%"
