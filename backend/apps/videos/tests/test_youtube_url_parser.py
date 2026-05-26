import pytest

from apps.videos.services.youtube_url_parser import parse_youtube_url, youtube_timestamp_url


@pytest.mark.parametrize(
    ("url", "video_id"),
    [
        ("https://www.youtube.com/watch?v=abc123XYZ_9", "abc123XYZ_9"),
        ("https://youtu.be/abc123XYZ_9", "abc123XYZ_9"),
        ("https://www.youtube.com/shorts/abc123XYZ_9", "abc123XYZ_9"),
    ],
)
def test_parse_video_urls(url, video_id):
    parsed = parse_youtube_url(url)
    assert parsed.type == "video"
    assert parsed.video_id == video_id
    assert parsed.canonical_url.startswith("https://youtube.com/watch?v=")


def test_parse_playlist_url():
    parsed = parse_youtube_url("https://www.youtube.com/playlist?list=PL123")
    assert parsed.type == "playlist"
    assert parsed.playlist_id == "PL123"


def test_rejects_non_youtube_host():
    with pytest.raises(ValueError):
        parse_youtube_url("https://example.com/watch?v=abc")


def test_timestamp_url():
    assert youtube_timestamp_url("abc", 123456) == "https://youtube.com/watch?v=abc&t=123s"
