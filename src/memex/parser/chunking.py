"""Chunking strategies for markdown content."""

from __future__ import annotations

from dataclasses import dataclass
import re

import tiktoken

from ..config import ChunkingConfig
from ..models import DocumentChunk, EntryMetadata

# Cached encoder for token counting (cl100k_base is Claude/GPT-4 compatible)
_encoder: tiktoken.Encoding | None = None


def _get_token_count(text: str) -> int:
    """Count tokens using cl100k_base encoding."""
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")
    return len(_encoder.encode(text))


@dataclass(frozen=True)
class ChunkSpan:
    """Chunk span with offsets for metadata."""

    content: str
    start_offset: int
    end_offset: int
    section: str | None = None
    parent_section: str | None = None


def chunk_content(
    path: str,
    content: str,
    metadata: EntryMetadata,
    config: ChunkingConfig | None = None,
) -> list[DocumentChunk]:
    """Chunk content using configured strategy."""
    config = config or ChunkingConfig()

    if not config.enabled:
        span = _build_span(content, 0, len(content), section=None)
        if not span:
            return []
        return [_span_to_chunk(path, span, metadata, chunk_idx=0, chunk_strategy="document")]

    strategy = (config.strategy or "headers").lower()
    if strategy == "headers":
        spans = chunk_by_headers(content)
    elif strategy == "paragraph":
        spans = chunk_by_paragraph(content)
    elif strategy == "sentences":
        spans = chunk_by_sentences(content)
    elif strategy == "semantic":
        spans = chunk_by_semantic(
            content,
            max_chunk_tokens=config.max_chunk_tokens,
            overlap_tokens=config.overlap_tokens,
            min_chunk_tokens=config.min_chunk_tokens,
        )
    else:
        spans = chunk_by_headers(content)

    return [
        _span_to_chunk(path, span, metadata, chunk_idx, strategy)
        for chunk_idx, span in enumerate(spans)
    ]


def chunk_by_headers(content: str) -> list[ChunkSpan]:
    """Split content into chunks by H2 headers."""
    h2_pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    matches = list(h2_pattern.finditer(content))
    chunks: list[ChunkSpan] = []

    if not matches:
        span = _build_span(content, 0, len(content), section=None)
        return [span] if span else []

    # Intro section (before first H2)
    intro_span = _build_span(content, 0, matches[0].start(), section=None)
    if intro_span:
        chunks.append(intro_span)

    for i, match in enumerate(matches):
        section_name = match.group(1).strip() or None
        section_start = match.end()
        section_end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        span = _build_span(
            content, section_start, section_end, section=section_name, parent_section=section_name
        )
        if span:
            chunks.append(span)

    return chunks


def chunk_by_paragraph(content: str) -> list[ChunkSpan]:
    """Split content into chunks by blank lines."""
    chunks: list[ChunkSpan] = []
    separator = re.compile(r"\n\s*\n")

    start = 0
    for match in separator.finditer(content):
        span = _build_span(content, start, match.start(), section=None)
        if span:
            chunks.append(span)
        start = match.end()

    tail = _build_span(content, start, len(content), section=None)
    if tail:
        chunks.append(tail)
    return chunks


def chunk_by_sentences(content: str) -> list[ChunkSpan]:
    """Split content into chunks per sentence."""
    chunks: list[ChunkSpan] = []
    for sentence, start, end in split_sentences_with_offsets(content):
        chunks.append(
            ChunkSpan(
                content=sentence,
                start_offset=start,
                end_offset=end,
                section=None,
                parent_section=None,
            )
        )
    return chunks


def chunk_by_semantic(
    content: str,
    max_chunk_tokens: int,
    overlap_tokens: int,
    min_chunk_tokens: int,
) -> list[ChunkSpan]:
    """Chunk content by sentence boundaries with token limits."""
    sentences = split_sentences_with_offsets(content)
    if not sentences:
        span = _build_span(content, 0, len(content), section=None)
        return [span] if span else []

    chunks: list[ChunkSpan] = []
    current: list[tuple[str, int, int]] = []
    current_tokens = 0

    def finalize_current() -> None:
        nonlocal current, current_tokens
        if not current:
            return
        start = current[0][1]
        end = current[-1][2]
        span = _build_span(content, start, end, section=None)
        if span:
            chunks.append(span)

    def build_overlap() -> list[tuple[str, int, int]]:
        if overlap_tokens <= 0 or not current:
            return []
        overlap: list[tuple[str, int, int]] = []
        overlap_count = 0
        for sentence in reversed(current):
            sentence_tokens = _get_token_count(sentence[0])
            overlap.insert(0, sentence)
            overlap_count += sentence_tokens
            if overlap_count >= overlap_tokens:
                break
        return overlap

    for sentence in sentences:
        sentence_text = sentence[0]
        sentence_tokens = _get_token_count(sentence_text)
        if current and current_tokens + sentence_tokens > max_chunk_tokens:
            finalize_current()
            current = build_overlap()
            current_tokens = sum(_get_token_count(s[0]) for s in current)

        current.append(sentence)
        current_tokens += sentence_tokens

    finalize_current()

    if min_chunk_tokens > 0 and len(chunks) > 1:
        last = chunks[-1]
        if _get_token_count(last.content) < min_chunk_tokens:
            prev = chunks[-2]
            merged = _build_span(content, prev.start_offset, last.end_offset, section=None)
            if merged:
                chunks[-2] = merged
                chunks.pop()

    return chunks


def split_sentences_with_offsets(content: str) -> list[tuple[str, int, int]]:
    """Split content into sentences with character offsets."""
    spans: list[tuple[str, int, int]] = []
    for start, end, is_code in _split_by_code_blocks(content):
        segment = content[start:end]
        if is_code:
            trimmed = _trim_span(content, start, end)
            if trimmed:
                spans.append(trimmed)
            continue

        for match in _sentence_pattern().finditer(segment):
            span_start = start + match.start()
            span_end = start + match.end()
            trimmed = _trim_span(content, span_start, span_end)
            if trimmed:
                spans.append(trimmed)

    return spans


def _sentence_pattern() -> re.Pattern[str]:
    return re.compile(r"[^.!?]+(?:[.!?]+|$)", re.DOTALL)


def _split_by_code_blocks(content: str) -> list[tuple[int, int, bool]]:
    """Split content into code-block and non-code spans."""
    code_spans: list[tuple[int, int]] = []
    in_code = False
    fence = ""
    block_start = 0

    for match in re.finditer(r"^.*(?:\n|$)", content, re.MULTILINE):
        line = match.group(0)
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_code:
                in_code = True
                fence = marker
                block_start = match.start()
            elif marker == fence:
                in_code = False
                code_spans.append((block_start, match.end()))

    if in_code:
        code_spans.append((block_start, len(content)))

    if not code_spans:
        return [(0, len(content), False)]

    spans: list[tuple[int, int, bool]] = []
    cursor = 0
    for start, end in code_spans:
        if cursor < start:
            spans.append((cursor, start, False))
        spans.append((start, end, True))
        cursor = end
    if cursor < len(content):
        spans.append((cursor, len(content), False))
    return spans


def _trim_span(content: str, start: int, end: int) -> tuple[str, int, int] | None:
    while start < end and content[start].isspace():
        start += 1
    while end > start and content[end - 1].isspace():
        end -= 1
    if start >= end:
        return None
    return content[start:end], start, end


def _build_span(
    content: str,
    start: int,
    end: int,
    section: str | None,
    parent_section: str | None = None,
) -> ChunkSpan | None:
    trimmed = _trim_span(content, start, end)
    if not trimmed:
        return None
    chunk_content, chunk_start, chunk_end = trimmed
    return ChunkSpan(
        content=chunk_content,
        start_offset=chunk_start,
        end_offset=chunk_end,
        section=section,
        parent_section=parent_section,
    )


def _span_to_chunk(
    path: str,
    span: ChunkSpan,
    metadata: EntryMetadata,
    chunk_idx: int,
    chunk_strategy: str,
) -> DocumentChunk:
    return DocumentChunk(
        path=path,
        section=span.section,
        parent_section=span.parent_section,
        chunk_idx=chunk_idx,
        chunk_strategy=chunk_strategy,
        start_offset=span.start_offset,
        end_offset=span.end_offset,
        content=span.content,
        metadata=metadata,
        token_count=_get_token_count(span.content),
    )


def build_document_chunk(
    path: str, content: str, metadata: EntryMetadata, chunk_strategy: str = "document"
) -> DocumentChunk | None:
    """Build a single DocumentChunk representing the full document."""
    span = _build_span(content, 0, len(content), section=None)
    if not span:
        return None
    return _span_to_chunk(path, span, metadata, chunk_idx=0, chunk_strategy=chunk_strategy)
