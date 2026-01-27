"""Search quality evaluation helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import log2
from pathlib import Path
from typing import Any

from .indexer import HybridSearcher
from .models import QualityDetail, QualityReport


@dataclass(frozen=True)
class EvalCase:
    query: str
    expected: list[str]
    tags: list[str] | None = None
    mode: str | None = None
    scope: str | None = None
    strict: bool | None = None

EVAL_QUERIES: Sequence[dict] = (
    {
        "query": "python tooling",
        "expected": ["development/python-tooling.md"],
    },
    {
        "query": "dokploy deployment",
        "expected": ["devops/deployment.md"],
    },
    {
        "query": "dockerfile uv",
        "expected": ["devops/docker-patterns.md"],
    },
    {
        "query": "devcontainer setup",
        "expected": ["infrastructure/devcontainers.md"],
    },
    {
        "query": "dns troubleshooting",
        "expected": ["troubleshooting/dns-resolution-issues.md"],
    },
)


def run_quality_checks(searcher: HybridSearcher, limit: int = 5, cutoff: int = 3) -> QualityReport:
    """Evaluate search accuracy against a fixed query set."""

    details: list[QualityDetail] = []
    successes = 0

    for case in EVAL_QUERIES:
        query = case["query"]
        expected = case["expected"]

        results = searcher.search(query, limit=limit, mode="hybrid")
        result_paths = [res.path for res in results]

        best_rank: int | None = None
        found = False

        for exp in expected:
            if exp in result_paths:
                rank = result_paths.index(exp) + 1
                best_rank = rank if best_rank is None else min(best_rank, rank)
                if rank <= cutoff:
                    found = True

        if found:
            successes += 1

        details.append(
            QualityDetail(
                query=query,
                expected=expected,
                hits=result_paths,
                found=found,
                best_rank=best_rank,
            )
        )

    total = len(EVAL_QUERIES)
    accuracy = successes / total if total else 1.0

    return QualityReport(accuracy=accuracy, total_queries=total, details=details)


def load_eval_cases(path: Path) -> list[EvalCase]:
    """Load evaluation cases from a JSON file."""
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Evaluation dataset must be a JSON array")

    cases: list[EvalCase] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Evaluation case {idx} must be an object")
        query = item.get("query")
        expected = item.get("expected")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"Evaluation case {idx} missing valid 'query'")
        if isinstance(expected, str):
            expected_list = [expected]
        elif isinstance(expected, list) and all(isinstance(x, str) for x in expected):
            expected_list = expected
        else:
            raise ValueError(f"Evaluation case {idx} missing valid 'expected' list")

        tags = item.get("tags")
        if isinstance(tags, str):
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        elif isinstance(tags, list) and all(isinstance(x, str) for x in tags):
            tags_list = tags
        else:
            tags_list = None

        mode = item.get("mode") if isinstance(item.get("mode"), str) else None
        scope = item.get("scope") if isinstance(item.get("scope"), str) else None
        strict = item.get("strict") if isinstance(item.get("strict"), bool) else None

        cases.append(
            EvalCase(
                query=query.strip(),
                expected=expected_list,
                tags=tags_list,
                mode=mode,
                scope=scope,
                strict=strict,
            )
        )

    return cases


def compute_metrics(result_paths: list[str], expected: list[str], k: int) -> dict[str, Any]:
    """Compute retrieval metrics for a single query."""
    expected_set = set(expected)
    hits = result_paths[:k]

    best_rank: int | None = None
    for idx, path in enumerate(result_paths, start=1):
        if path in expected_set:
            best_rank = idx
            break

    recall = 0.0
    if expected_set:
        recall = len({path for path in hits if path in expected_set}) / len(expected_set)

    mrr = 1.0 / best_rank if best_rank else 0.0

    dcg = 0.0
    for idx, path in enumerate(hits, start=1):
        if path in expected_set:
            dcg += 1.0 / log2(idx + 1)

    ideal_count = min(k, len(expected_set))
    idcg = sum(1.0 / log2(idx + 1) for idx in range(1, ideal_count + 1))
    ndcg = dcg / idcg if idcg > 0 else 0.0

    hit = bool(best_rank and best_rank <= k)

    return {
        "best_rank": best_rank,
        "recall": recall,
        "mrr": mrr,
        "ndcg": ndcg,
        "hit": hit,
        "hits": hits,
    }


def aggregate_metrics(per_query: list[dict[str, Any]], k: int) -> dict[str, Any]:
    """Aggregate metrics across queries."""
    if not per_query:
        return {
            "k": k,
            "queries": 0,
            "recall@k": 0.0,
            "mrr": 0.0,
            "ndcg@k": 0.0,
            "hit_rate@k": 0.0,
        }

    recall = sum(item["recall"] for item in per_query) / len(per_query)
    mrr = sum(item["mrr"] for item in per_query) / len(per_query)
    ndcg = sum(item["ndcg"] for item in per_query) / len(per_query)
    hit_rate = sum(1 for item in per_query if item["hit"]) / len(per_query)

    return {
        "k": k,
        "queries": len(per_query),
        "recall@k": recall,
        "mrr": mrr,
        "ndcg@k": ndcg,
        "hit_rate@k": hit_rate,
    }
