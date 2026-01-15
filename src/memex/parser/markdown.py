"""Markdown parsing with YAML frontmatter support."""

from pathlib import Path

import frontmatter
from pydantic import ValidationError

from ..config import get_chunking_config
from ..models import DocumentChunk, EntryMetadata
from .chunking import chunk_content


class ParseError(Exception):
    """Raised when markdown parsing fails."""

    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


def parse_entry(path: Path) -> tuple[EntryMetadata, str, list[DocumentChunk]]:
    """Parse a markdown file with YAML frontmatter.

    Args:
        path: Path to the markdown file.

    Returns:
        Tuple of (metadata, raw_content, chunks).

    Raises:
        ParseError: If the file cannot be parsed or has invalid frontmatter.
    """
    if not path.exists():
        raise ParseError(path, "File does not exist")

    if not path.is_file():
        raise ParseError(path, "Path is not a file")

    try:
        post = frontmatter.load(str(path))
    except Exception as e:
        raise ParseError(path, f"Failed to parse frontmatter: {e}") from e

    if not post.metadata:
        raise ParseError(path, "Missing frontmatter (YAML block required at start of file)")

    try:
        metadata = EntryMetadata.model_validate(post.metadata)
    except ValidationError as e:
        errors = []
        for error in e.errors():
            loc = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            errors.append(f"  - {loc}: {msg}")
        raise ParseError(path, "Invalid frontmatter:\n" + "\n".join(errors)) from e

    content = post.content
    path_str = str(path)

    chunking_config = get_chunking_config()
    chunks = chunk_content(path_str, content, metadata, chunking_config)

    return metadata, content, chunks
