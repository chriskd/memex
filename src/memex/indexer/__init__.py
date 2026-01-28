"""Search indexing with hybrid Whoosh + Chroma.

Note: Heavy dependencies (chromadb, sentence-transformers, torch) are lazily loaded.
Import HybridSearcher, ChromaIndex, etc. only when actually needed for search.
"""

import re
from typing import TYPE_CHECKING

# Type hints only - no runtime import of heavy deps
if TYPE_CHECKING:
    from .chroma_index import ChromaIndex
    from .hybrid import HybridSearcher
    from .watcher import FileWatcher
    from .whoosh_index import WhooshIndex

__all__ = [
    "HybridSearcher",
    "WhooshIndex",
    "ChromaIndex",
    "FileWatcher",
    "strip_markdown_for_snippet",
    "get_searcher",
]


def __getattr__(name: str):
    """Lazy import for heavy search dependencies."""
    if name == "HybridSearcher":
        from .hybrid import HybridSearcher
        return HybridSearcher
    if name == "WhooshIndex":
        from .whoosh_index import WhooshIndex
        return WhooshIndex
    if name == "ChromaIndex":
        from .chroma_index import ChromaIndex
        return ChromaIndex
    if name == "FileWatcher":
        from .watcher import FileWatcher
        return FileWatcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_searcher():
    """Get HybridSearcher instance, raising helpful error if deps missing."""
    try:
        from .hybrid import HybridSearcher
        return HybridSearcher
    except ImportError as e:
        raise ImportError(
            "Search functionality requires additional dependencies. "
            "Install with: pip install 'memex-kb[search]'"
        ) from e


def strip_markdown_for_snippet(text: str, max_length: int = 200) -> str:
    """Strip markdown syntax from text to create a clean snippet.

    Removes tables, code fences, headers, links, and other formatting
    to produce readable plain text for search result previews.

    Args:
        text: Raw markdown text.
        max_length: Maximum snippet length (default 200).

    Returns:
        Cleaned text suitable for display as a snippet.
    """
    if not text:
        return ""

    # Remove code fences (```...```)
    text = re.sub(r"```[\s\S]*?```", " ", text)

    # Remove inline code (`...`)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Remove table formatting - pipes and alignment rows
    text = re.sub(r"\|", " ", text)
    text = re.sub(r"^[\s\-:]+$", "", text, flags=re.MULTILINE)

    # Remove header markers
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

    # Remove bold/italic markers
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)

    # Remove links but keep text: [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Remove wikilinks: [[link]] -> link, [[link|alias]] -> alias
    text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)

    # Remove blockquote markers
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)

    # Remove list markers
    text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[\s]*\d+\.\s+", "", text, flags=re.MULTILINE)

    # Collapse multiple whitespace/newlines
    text = re.sub(r"\s+", " ", text).strip()

    # Truncate
    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text
