from dataclasses import dataclass

from apps.videos.services.chunker import chunk_segments


@dataclass
class Segment:
    start_ms: int
    end_ms: int
    text: str


def test_chunking_preserves_first_and_last_timestamps():
    segments = [Segment(i * 1000, i * 1000 + 900, "word " * 20) for i in range(20)]
    chunks = chunk_segments(segments, min_tokens=40, max_tokens=120, overlap_tokens=20)
    assert chunks[0].start_ms == 0
    assert chunks[0].end_ms >= 3900
    assert chunks[-1].end_ms == segments[-1].end_ms


def test_chunking_splits_single_long_segment_with_interpolated_timestamps():
    text = " ".join(f"Sentence {index} has useful searchable context." for index in range(120))
    chunks = chunk_segments([Segment(0, 120000, text)], min_tokens=120, max_tokens=260, overlap_tokens=40)

    assert len(chunks) > 1
    assert chunks[0].start_ms == 0
    assert chunks[-1].end_ms == 120000
    assert all(chunk.token_count <= 260 for chunk in chunks)
    assert all(chunks[index].start_ms <= chunks[index].end_ms for index in range(len(chunks)))


def test_chunking_avoids_tiny_final_chunk_when_possible():
    segments = [Segment(index * 1000, index * 1000 + 900, "word " * 15) for index in range(9)]
    chunks = chunk_segments(segments, min_tokens=80, max_tokens=260, overlap_tokens=20)

    assert len(chunks) == 1
    assert chunks[0].end_ms == segments[-1].end_ms
