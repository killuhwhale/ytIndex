from __future__ import annotations

from dataclasses import dataclass


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
    chunks: list[TranscriptChunkData] = []
    current = []
    current_tokens = 0

    for segment in segments:
        segment_tokens = approximate_tokens(segment.text)
        if current and current_tokens + segment_tokens > max_tokens:
            chunks.append(_build_chunk(len(chunks), current))
            current = _overlap_tail(current, overlap_tokens)
            current_tokens = sum(approximate_tokens(item.text) for item in current)
        current.append(segment)
        current_tokens += segment_tokens

    if current:
        chunks.append(_build_chunk(len(chunks), current))
    return chunks


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
