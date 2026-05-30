from dataclasses import dataclass

from apps.videos.services.summarizer import _fallback_summary, _normalize_summary


@dataclass
class Chunk:
    chunk_index: int
    start_ms: int
    end_ms: int
    text: str


def test_normalize_summary_fills_missing_schema_keys():
    data = _normalize_summary({"short_summary": "Useful summary", "key_points": "not-a-list"})

    assert data["short_summary"] == "Useful summary"
    assert data["detailed_summary"] == "Useful summary"
    assert data["key_points"] == []
    assert data["topics"] == []
    assert data["important_quotes"] == []


def test_fallback_summary_does_not_echo_timestamp_markers():
    summary = _fallback_summary("[1-68] First meaningful point about the debt. [69-120] Later consequences are explained clearly.")

    assert "[1-68]" not in summary["short_summary"]
    assert "First meaningful point" in summary["short_summary"]
