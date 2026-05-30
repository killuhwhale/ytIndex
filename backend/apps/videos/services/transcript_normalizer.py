from __future__ import annotations

import html
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedSegment:
    start_ms: int
    end_ms: int
    text: str
    segment_index: int
    confidence: float | None = None


TIME_RE = re.compile(r"(?:(\d+):)?(\d{2}):(\d{2})[,.](\d{3})")
TAGS_RE = re.compile(r"<[^>]+>")


def parse_time_ms(value: str) -> int:
    match = TIME_RE.search(value)
    if not match:
        raise ValueError(f"Invalid timestamp: {value}")
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    millis = int(match.group(4))
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def clean_caption_text(text: str) -> str:
    text = TAGS_RE.sub("", html.unescape(text))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_transcript(raw_text: str, raw_format: str) -> list[NormalizedSegment]:
    if raw_format == "vtt":
        return _parse_vtt_or_srt(raw_text, skip_headers=True)
    if raw_format == "srt":
        return _parse_vtt_or_srt(raw_text, skip_headers=False)
    if raw_format == "plain_text":
        text = clean_caption_text(raw_text)
        return [NormalizedSegment(0, max(1000, len(text.split()) * 450), text, 0)] if text else []
    raise ValueError(f"Unsupported transcript format: {raw_format}")


def _parse_vtt_or_srt(raw_text: str, skip_headers: bool) -> list[NormalizedSegment]:
    segments: list[NormalizedSegment] = []
    current_time: tuple[int, int] | None = None
    current_lines: list[str] = []

    for raw_line in raw_text.splitlines() + [""]:
        line = raw_line.strip("\ufeff ").strip()
        if skip_headers and (line == "WEBVTT" or line.startswith(("Kind:", "Language:", "NOTE"))):
            continue
        if "-->" in line:
            if current_time and current_lines:
                _append_segment(segments, current_time, current_lines)
            start, end = [part.strip().split(" ")[0] for part in line.split("-->", 1)]
            current_time = (parse_time_ms(start), parse_time_ms(end))
            current_lines = []
        elif not line or line.isdigit():
            if current_time and current_lines:
                _append_segment(segments, current_time, current_lines)
            current_time = None
            current_lines = []
        elif current_time:
            current_lines.append(line)

    return _split_long_segments(_collapse_rolling_captions(segments))


def _append_segment(segments: list[NormalizedSegment], time_pair: tuple[int, int], lines: list[str]) -> None:
    text = clean_caption_text(" ".join(lines))
    if text and (not segments or segments[-1].text != text):
        segments.append(NormalizedSegment(time_pair[0], time_pair[1], text, len(segments)))


def _collapse_rolling_captions(segments: list[NormalizedSegment]) -> list[NormalizedSegment]:
    collapsed: list[NormalizedSegment] = []
    for segment in segments:
        if not collapsed:
            collapsed.append(segment)
            continue

        previous = collapsed[-1]
        if segment.start_ms - previous.end_ms > 2500:
            collapsed.append(NormalizedSegment(segment.start_ms, segment.end_ms, segment.text, len(collapsed)))
            continue

        merged_text = _merge_overlapping_text(previous.text, segment.text)
        if merged_text == previous.text:
            collapsed[-1] = NormalizedSegment(previous.start_ms, max(previous.end_ms, segment.end_ms), previous.text, previous.segment_index)
        elif merged_text:
            collapsed[-1] = NormalizedSegment(previous.start_ms, max(previous.end_ms, segment.end_ms), merged_text, previous.segment_index)
        else:
            collapsed.append(NormalizedSegment(segment.start_ms, segment.end_ms, segment.text, len(collapsed)))
    return [NormalizedSegment(item.start_ms, item.end_ms, item.text, index) for index, item in enumerate(collapsed)]


def _merge_overlapping_text(previous: str, current: str) -> str | None:
    if current == previous or current in previous:
        return previous
    if previous in current:
        return current

    previous_words = previous.split()
    current_words = current.split()
    max_overlap = min(len(previous_words), len(current_words))
    for size in range(max_overlap, 2, -1):
        if _words_equal(previous_words[-size:], current_words[:size]):
            suffix = current_words[size:]
            return " ".join(previous_words + suffix)
    return None


def _words_equal(left: list[str], right: list[str]) -> bool:
    return [_normalize_word(word) for word in left] == [_normalize_word(word) for word in right]


def _normalize_word(word: str) -> str:
    return re.sub(r"\W+", "", word).lower()


def _split_long_segments(segments: list[NormalizedSegment], max_words: int = 34, max_duration_ms: int = 12000) -> list[NormalizedSegment]:
    output: list[NormalizedSegment] = []
    for segment in segments:
        if len(segment.text.split()) <= max_words and segment.end_ms - segment.start_ms <= max_duration_ms:
            output.append(NormalizedSegment(segment.start_ms, segment.end_ms, segment.text, len(output), segment.confidence))
            continue
        output.extend(_split_segment(segment, len(output), _target_words_for_segment(segment, max_words, max_duration_ms)))
    return [NormalizedSegment(item.start_ms, item.end_ms, item.text, index, item.confidence) for index, item in enumerate(output)]


def _split_segment(segment: NormalizedSegment, start_index: int, max_words: int) -> list[NormalizedSegment]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", segment.text) if part.strip()]
    if len(parts) <= 1:
        words = segment.text.split()
        parts = [" ".join(words[index : index + max_words]) for index in range(0, len(words), max_words)]

    groups: list[str] = []
    current: list[str] = []
    for part in parts:
        current_words = sum(len(item.split()) for item in current)
        part_words = len(part.split())
        if current and current_words + part_words > max_words:
            groups.append(" ".join(current))
            current = []
        current.append(part)
    if current:
        groups.append(" ".join(current))

    total_words = max(1, sum(len(group.split()) for group in groups))
    duration = max(1, segment.end_ms - segment.start_ms)
    elapsed_words = 0
    split_segments = []
    for offset, group in enumerate(groups):
        words = max(1, len(group.split()))
        start_ms = segment.start_ms + int(duration * elapsed_words / total_words)
        elapsed_words += words
        end_ms = segment.start_ms + int(duration * elapsed_words / total_words)
        split_segments.append(
            NormalizedSegment(
                start_ms=start_ms,
                end_ms=max(start_ms + 1, end_ms),
                text=group,
                segment_index=start_index + offset,
                confidence=segment.confidence,
            )
        )
    return split_segments


def _target_words_for_segment(segment: NormalizedSegment, max_words: int, max_duration_ms: int) -> int:
    duration = max(1, segment.end_ms - segment.start_ms)
    target_parts = max(1, (duration + max_duration_ms - 1) // max_duration_ms)
    total_words = max(1, len(segment.text.split()))
    return max(8, min(max_words, (total_words + target_parts - 1) // target_parts))


def _merge_tiny_segments(segments: list[NormalizedSegment]) -> list[NormalizedSegment]:
    merged: list[NormalizedSegment] = []
    buffer: NormalizedSegment | None = None
    for segment in segments:
        if buffer is None:
            buffer = segment
            continue
        if len(buffer.text.split()) < 4 and segment.start_ms - buffer.end_ms < 1500:
            buffer = NormalizedSegment(buffer.start_ms, segment.end_ms, f"{buffer.text} {segment.text}", len(merged))
        else:
            merged.append(NormalizedSegment(buffer.start_ms, buffer.end_ms, buffer.text, len(merged)))
            buffer = segment
    if buffer:
        merged.append(NormalizedSegment(buffer.start_ms, buffer.end_ms, buffer.text, len(merged)))
    return merged
