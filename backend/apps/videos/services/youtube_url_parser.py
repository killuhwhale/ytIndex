from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"}


@dataclass(frozen=True)
class ParsedYouTubeUrl:
    type: str
    video_id: str | None
    playlist_id: str | None
    canonical_url: str


class YouTubeUrlError(ValueError):
    pass


def parse_youtube_url(url: str) -> ParsedYouTubeUrl:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    if host not in ALLOWED_HOSTS:
        raise YouTubeUrlError("Only recognized YouTube hostnames are allowed.")

    query = parse_qs(parsed.query)
    video_id: str | None = None
    playlist_id = query.get("list", [None])[0]

    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0] or None
    elif parsed.path == "/watch":
        video_id = query.get("v", [None])[0]
    elif parsed.path.startswith("/shorts/"):
        video_id = parsed.path.split("/")[2] or None
    elif parsed.path.startswith("/playlist"):
        playlist_id = playlist_id

    if not video_id and not playlist_id:
        raise YouTubeUrlError("URL must contain a YouTube video id or playlist id.")

    if playlist_id and not video_id:
        return ParsedYouTubeUrl(
            type="playlist",
            video_id=None,
            playlist_id=playlist_id,
            canonical_url=f"https://www.youtube.com/playlist?list={playlist_id}",
        )

    canonical = f"https://youtube.com/watch?v={video_id}"
    if playlist_id:
        canonical = f"{canonical}&list={playlist_id}"
    return ParsedYouTubeUrl(type="video", video_id=video_id, playlist_id=playlist_id, canonical_url=canonical)


def split_input_urls(input_text: str) -> list[str]:
    return [line.strip() for line in input_text.replace(",", "\n").splitlines() if line.strip()]


def youtube_timestamp_url(youtube_video_id: str, start_ms: int) -> str:
    return f"https://youtube.com/watch?v={youtube_video_id}&t={max(start_ms, 0) // 1000}s"
