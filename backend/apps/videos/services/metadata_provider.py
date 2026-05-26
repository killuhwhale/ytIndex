from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings


@dataclass(frozen=True)
class VideoMetadata:
    youtube_video_id: str
    source_url: str
    canonical_url: str
    title: str
    description: str = ""
    channel_id: str | None = None
    channel_title: str | None = None
    thumbnail_url: str | None = None
    duration_seconds: int | None = None
    metadata_json: dict | None = None


def fetch_video_metadata(parsed, source_url: str) -> VideoMetadata:
    if settings.YOUTUBE_API_KEY:
        # Kept small for MVP: video lookup can be expanded to parse ISO-8601 durations and stats.
        api_url = (
            "https://www.googleapis.com/youtube/v3/videos"
            f"?part=snippet,contentDetails,statistics&id={parsed.video_id}&key={settings.YOUTUBE_API_KEY}"
        )
        with urlopen(api_url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        items = payload.get("items", [])
        if items:
            item = items[0]
            snippet = item.get("snippet", {})
            thumbnails = snippet.get("thumbnails", {})
            thumb = thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default") or {}
            return VideoMetadata(
                youtube_video_id=parsed.video_id,
                source_url=source_url,
                canonical_url=parsed.canonical_url,
                title=snippet.get("title") or parsed.video_id,
                description=snippet.get("description", ""),
                channel_id=snippet.get("channelId"),
                channel_title=snippet.get("channelTitle"),
                thumbnail_url=thumb.get("url"),
                metadata_json=item,
            )

    return VideoMetadata(
        youtube_video_id=parsed.video_id,
        source_url=source_url,
        canonical_url=parsed.canonical_url,
        title=f"YouTube video {parsed.video_id}",
        thumbnail_url=f"https://img.youtube.com/vi/{parsed.video_id}/hqdefault.jpg",
        metadata_json={"provider": "fallback"},
    )


def fetch_playlist_video_urls(playlist_id: str) -> list[str]:
    if not settings.YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY is required to expand playlist URLs.")

    urls: list[str] = []
    page_token = ""
    while True:
        params = {
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": "50",
            "key": settings.YOUTUBE_API_KEY,
        }
        if page_token:
            params["pageToken"] = page_token
        with urlopen(f"https://www.googleapis.com/youtube/v3/playlistItems?{urlencode(params)}", timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        for item in payload.get("items", []):
            video_id = item.get("contentDetails", {}).get("videoId")
            if video_id:
                urls.append(f"https://youtube.com/watch?v={video_id}")
        page_token = payload.get("nextPageToken", "")
        if not page_token:
            break
    return urls
