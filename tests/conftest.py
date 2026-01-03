import importlib.util

import pytest


def _semantic_deps_available() -> bool:
    return (
        importlib.util.find_spec("chromadb") is not None
        and importlib.util.find_spec("sentence_transformers") is not None
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "semantic: requires chromadb and sentence-transformers extras",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _semantic_deps_available():
        return

    skip_semantic = pytest.mark.skip(
        reason=(
            "semantic extras not installed; install with "
            "`uv pip install -e '.[semantic]'` to run these tests"
        )
    )

    for item in items:
        if "semantic" in item.keywords:
            item.add_marker(skip_semantic)
