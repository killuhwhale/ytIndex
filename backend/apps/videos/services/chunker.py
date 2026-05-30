from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TranscriptChunkData:
    chunk_index: int
    start_ms: int
    end_ms: int
    text: str
    token_count: int


def approximate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) * 1.3))


def chunk_segments(segments, min_tokens: int = 400, max_tokens: int = 900, overlap_tokens: int = 80) -> list[TranscriptChunkData]:
    segments = _prepare_segments(list(segments), max_tokens=max_tokens)
    chunks: list[TranscriptChunkData] = []
    current = []
    current_tokens = 0

    for segment in segments:
        segment_tokens = approximate_tokens(segment.text)
        if current and current_tokens + segment_tokens > max_tokens and current_tokens >= min_tokens:
            chunks.append(_build_chunk(len(chunks), current))
            current = _overlap_tail(current, overlap_tokens)
            current_tokens = sum(approximate_tokens(item.text) for item in current)
            if current and current_tokens + segment_tokens > max_tokens:
                current = []
                current_tokens = 0
        current.append(segment)
        current_tokens += segment_tokens

    if current:
        if chunks and current_tokens < min_tokens:
            chunks = _rebalance_small_tail(chunks, current, max_tokens)
        else:
            chunks.append(_build_chunk(len(chunks), current))
    return _renumber(chunks)


def _build_chunk(index: int, segments) -> TranscriptChunkData:
    text = " ".join(segment.text for segment in segments).strip()
    return TranscriptChunkData(
        chunk_index=index,
        start_ms=segments[0].start_ms,
        end_ms=segments[-1].end_ms,
        text=text,
        token_count=approximate_tokens(text),
    )


def _overlap_tail(segments, overlap_tokens: int):
    tail = []
    tokens = 0
    for segment in reversed(segments):
        tail.insert(0, segment)
        tokens += approximate_tokens(segment.text)
        if tokens >= overlap_tokens:
            break
    return tail


def _prepare_segments(segments: list, max_tokens: int) -> list:
    prepared = []
    target_tokens = max(80, min(260, max_tokens // 2))
    for segment in segments:
        if approximate_tokens(segment.text) <= max_tokens:
            prepared.append(segment)
            continue
        prepared.extend(_split_oversized_segment(segment, target_tokens))
    return prepared


def _split_oversized_segment(segment, target_tokens: int) -> list:
    parts = _sentence_parts(segment.text)
    if len(parts) <= 1:
        parts = _word_parts(segment.text, target_tokens)

    grouped: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for part in parts:
        part_tokens = approximate_tokens(part)
        if current and current_tokens + part_tokens > target_tokens:
            grouped.append(" ".join(current).strip())
            current = []
            current_tokens = 0
        current.append(part)
        current_tokens += part_tokens
    if current:
        grouped.append(" ".join(current).strip())

    total_words = max(1, sum(len(text.split()) for text in grouped))
    duration = max(1, segment.end_ms - segment.start_ms)
    output = []
    elapsed_words = 0
    for text in grouped:
        word_count = max(1, len(text.split()))
        start_ms = segment.start_ms + int(duration * elapsed_words / total_words)
        elapsed_words += word_count
        end_ms = segment.start_ms + int(duration * elapsed_words / total_words)
        output.append(_Segment(start_ms=start_ms, end_ms=max(start_ms + 1, end_ms), text=text))
    return output


def _sentence_parts(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return parts if len(parts) > 1 else [text.strip()] if text.strip() else []


def _word_parts(text: str, target_tokens: int) -> list[str]:
    words = text.split()
    words_per_part = max(40, int(target_tokens / 1.3))
    return [" ".join(words[index : index + words_per_part]) for index in range(0, len(words), words_per_part)]


def _rebalance_small_tail(chunks: list[TranscriptChunkData], tail_segments: list, max_tokens: int) -> list[TranscriptChunkData]:
    last = chunks[-1]
    combined_text = f"{last.text} {' '.join(segment.text for segment in tail_segments)}".strip()
    if approximate_tokens(combined_text) <= max_tokens:
        chunks[-1] = TranscriptChunkData(
            chunk_index=last.chunk_index,
            start_ms=last.start_ms,
            end_ms=tail_segments[-1].end_ms,
            text=combined_text,
            token_count=approximate_tokens(combined_text),
        )
    else:
        chunks.append(_build_chunk(len(chunks), tail_segments))
    return chunks


def _renumber(chunks: list[TranscriptChunkData]) -> list[TranscriptChunkData]:
    return [
        TranscriptChunkData(
            chunk_index=index,
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
            text=chunk.text,
            token_count=chunk.token_count,
        )
        for index, chunk in enumerate(chunks)
    ]


@dataclass(frozen=True)
class _Segment:
    start_ms: int
    end_ms: int
    text: str
