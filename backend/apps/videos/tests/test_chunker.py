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
