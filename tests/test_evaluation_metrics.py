from __future__ import annotations

from math import log2

from memex.evaluation import aggregate_metrics, compute_metrics


def test_compute_metrics_perfect_hit() -> None:
    metrics = compute_metrics(["a.md", "b.md"], ["a.md"], k=2)
    assert metrics["best_rank"] == 1
    assert metrics["recall"] == 1.0
    assert metrics["mrr"] == 1.0
    assert metrics["ndcg"] == 1.0
    assert metrics["hit"] is True


def test_compute_metrics_second_rank() -> None:
    metrics = compute_metrics(["a.md", "b.md", "c.md"], ["b.md"], k=3)
    assert metrics["best_rank"] == 2
    assert metrics["recall"] == 1.0
    assert metrics["mrr"] == 0.5
    expected_ndcg = (1.0 / log2(3)) / (1.0 / log2(2))
    assert metrics["ndcg"] == expected_ndcg


def test_aggregate_metrics() -> None:
    per_query = [
        {"recall": 1.0, "mrr": 1.0, "ndcg": 1.0, "hit": True},
        {"recall": 0.0, "mrr": 0.0, "ndcg": 0.0, "hit": False},
    ]
    summary = aggregate_metrics(per_query, k=5)
    assert summary["queries"] == 2
    assert summary["recall@k"] == 0.5
    assert summary["mrr"] == 0.5
    assert summary["ndcg@k"] == 0.5
    assert summary["hit_rate@k"] == 0.5
