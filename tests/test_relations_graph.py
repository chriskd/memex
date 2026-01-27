"""Tests for unified relations graph."""

from pathlib import Path

from memex.relations_graph import build_relations_graph, query_relations_graph


def _write_entry(
    kb_root: Path,
    path: str,
    title: str,
    tags: list[str],
    content: str,
    relations: list[dict] | None = None,
    semantic_links: list[dict] | None = None,
) -> None:
    entry_path = kb_root / path
    entry_path.parent.mkdir(parents=True, exist_ok=True)

    tags_str = f"[{', '.join(tags)}]"
    relations_yaml = ""
    if relations:
        relations_yaml = "relations:\n"
        for relation in relations:
            relations_yaml += f"  - path: {relation['path']}\n"
            relations_yaml += f"    type: {relation['type']}\n"

    semantic_yaml = ""
    if semantic_links:
        semantic_yaml = "semantic_links:\n"
        for link in semantic_links:
            semantic_yaml += f"  - path: {link['path']}\n"
            semantic_yaml += f"    score: {link['score']}\n"
            semantic_yaml += f"    reason: {link['reason']}\n"

    frontmatter = f"""---
title: {title}
tags: {tags_str}
created: 2024-01-15
{semantic_yaml}{relations_yaml}---

{content}
"""
    entry_path.write_text(frontmatter)


class TestRelationsGraph:
    def test_builds_wikilink_and_frontmatter_edges(self, tmp_kb: Path) -> None:
        _write_entry(
            tmp_kb,
            "a.md",
            "Entry A",
            ["test"],
            "See [[b]] for more.",
            relations=[{"path": "c.md", "type": "depends_on"}],
        )
        _write_entry(tmp_kb, "b.md", "Entry B", ["test"], "Content B")
        _write_entry(tmp_kb, "c.md", "Entry C", ["test"], "Content C")

        graph = build_relations_graph()

        assert "a.md" in graph.nodes
        assert "b.md" in graph.nodes
        assert "c.md" in graph.nodes

        edge_keys = {
            (edge.source, edge.target, edge.origin, edge.relation_type) for edge in graph.edges
        }
        assert ("a.md", "b.md", "wikilink", None) in edge_keys
        assert ("a.md", "c.md", "relations", "depends_on") in edge_keys

    def test_query_filters_by_origin(self, tmp_kb: Path) -> None:
        _write_entry(
            tmp_kb,
            "a.md",
            "Entry A",
            ["test"],
            "See [[b]] for more.",
            relations=[{"path": "c.md", "type": "related"}],
        )
        _write_entry(tmp_kb, "b.md", "Entry B", ["test"], "Content B")
        _write_entry(tmp_kb, "c.md", "Entry C", ["test"], "Content C")

        result = query_relations_graph("a.md", origin={"relations"})
        assert result.edges
        assert all(edge.origin == "relations" for edge in result.edges)

    def test_builds_semantic_edges(self, tmp_kb: Path) -> None:
        _write_entry(
            tmp_kb,
            "a.md",
            "Entry A",
            ["test"],
            "Content A",
            semantic_links=[
                {"path": "b.md", "score": 0.72, "reason": "embedding_similarity"}
            ],
        )
        _write_entry(tmp_kb, "b.md", "Entry B", ["test"], "Content B")

        graph = build_relations_graph()

        edge_keys = {
            (edge.source, edge.target, edge.origin, edge.relation_type) for edge in graph.edges
        }
        assert ("a.md", "b.md", "semantic", None) in edge_keys
        semantic_edge = next(
            e
            for e in graph.edges
            if e.source == "a.md" and e.target == "b.md" and e.origin == "semantic"
        )
        assert semantic_edge.score == 0.72
