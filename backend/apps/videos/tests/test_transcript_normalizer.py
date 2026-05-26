from apps.videos.services.transcript_normalizer import normalize_transcript


def test_normalize_vtt_preserves_timestamps():
    raw = """WEBVTT

00:00:01.000 --> 00:00:03.500
Hello <c>world</c>

00:00:04.000 --> 00:00:05.000
Next line
"""
    segments = normalize_transcript(raw, "vtt")
    assert segments[0].start_ms == 1000
    assert segments[0].end_ms == 3500
    assert segments[0].text == "Hello world"


def test_normalize_srt_preserves_timestamps():
    raw = """1
00:00:02,000 --> 00:00:04,000
Hello there

2
00:00:05,000 --> 00:00:06,000
General Kenobi
"""
    segments = normalize_transcript(raw, "srt")
    assert segments[0].start_ms == 2000
    assert segments[-1].end_ms == 6000


def test_normalize_vtt_collapses_rolling_auto_caption_duplicates():
    raw = """WEBVTT

00:00:01.000 --> 00:00:02.000
All right, so we are beginning to see a

00:00:01.500 --> 00:00:04.000
All right, so we are beginning to see a good few people out there in the

00:00:02.000 --> 00:00:03.000
good few people out there in the

00:00:02.500 --> 00:00:05.000
good few people out there in the Runescape community begin to sound the

00:00:05.000 --> 00:00:06.000
Runescape community begin to sound the

00:00:05.500 --> 00:00:08.000
Runescape community begin to sound the alarm.
"""
    segments = normalize_transcript(raw, "vtt")
    full_text = " ".join(segment.text for segment in segments)
    assert full_text == "All right, so we are beginning to see a good few people out there in the Runescape community begin to sound the alarm."
    assert len(segments) == 1
    assert segments[0].start_ms == 1000
    assert segments[0].end_ms == 8000
