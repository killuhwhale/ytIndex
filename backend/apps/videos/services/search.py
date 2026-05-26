from __future__ import annotations

from dataclasses import dataclass

from django.contrib.postgres.search import SearchQuery, SearchRank

from ..models import SearchQueryLog, TranscriptChunk
from .embeddings import embed_texts
from .youtube_url_parser import youtube_timestamp_url


@dataclass(frozen=True)
class SearchResult:
    video_id: str
    youtube_video_id: str
    title: str
    channel_title: str | None
    thumbnail_url: str | None
    start_ms: int
    end_ms: int
    youtube_timestamp_url: str
    snippet: str
    score: float
    match_type: str
    why: str


def search_transcripts(query: str, search_type: str = "hybrid", limit: int = 20, filters: dict | None = None) -> list[dict]:
    filters = filters or {}
    if search_type == "keyword":
        results = _keyword(query, limit, filters)
    elif search_type == "semantic":
        results = _semantic(query, limit, filters)
    else:
        results = _hybrid(query, limit, filters)
    SearchQueryLog.objects.create(query_text=query, search_type=search_type, filters_json=filters, result_count=len(results))
    return [result.__dict__ for result in results]


def _base_queryset(filters: dict):
    qs = TranscriptChunk.objects.select_related("video")
    channel = filters.get("channel")
    if channel:
        qs = qs.filter(video__channel_title__icontains=channel)
    return qs


def _keyword(query: str, limit: int, filters: dict) -> list[SearchResult]:
    search_query = SearchQuery(query)
    qs = (
        _base_queryset(filters)
        .annotate(rank=SearchRank("search_vector", search_query))
        .filter(search_vector=search_query)
        .order_by("-rank")[:limit]
    )
    return [_to_result(chunk, float(chunk.rank or 0), "keyword", query) for chunk in qs]


def _semantic(query: str, limit: int, filters: dict) -> list[SearchResult]:
    from pgvector.django import CosineDistance

    vector = embed_texts([query])[0]
    qs = _base_queryset(filters).exclude(embedding__isnull=True).annotate(distance=CosineDistance("embedding", vector)).order_by("distance")[:limit]
    return [_to_result(chunk, max(0.0, 1.0 - float(chunk.distance or 1)), "semantic", query) for chunk in qs]


def _hybrid(query: str, limit: int, filters: dict) -> list[SearchResult]:
    combined: dict[str, SearchResult] = {}
    for result in _keyword(query, limit * 2, filters):
        combined[result.video_id + result.snippet[:40]] = result
    for result in _semantic(query, limit * 2, filters):
        key = result.video_id + result.snippet[:40]
        existing = combined.get(key)
        if existing:
            score = 0.45 * existing.score + 0.55 * result.score
            combined[key] = SearchResult(**{**existing.__dict__, "score": score, "match_type": "hybrid"})
        else:
            combined[key] = SearchResult(**{**result.__dict__, "score": 0.55 * result.score, "match_type": "hybrid"})
    diversified = sorted(combined.values(), key=lambda item: item.score, reverse=True)
    counts: dict[str, int] = {}
    output: list[SearchResult] = []
    for result in diversified:
        if counts.get(result.video_id, 0) >= 3:
            continue
        counts[result.video_id] = counts.get(result.video_id, 0) + 1
        output.append(result)
        if len(output) >= limit:
            break
    return output


def _to_result(chunk, score: float, match_type: str, query: str) -> SearchResult:
    video = chunk.video
    return SearchResult(
        video_id=str(video.id),
        youtube_video_id=video.youtube_video_id,
        title=video.title,
        channel_title=video.channel_title,
        thumbnail_url=video.thumbnail_url,
        start_ms=chunk.start_ms,
        end_ms=chunk.end_ms,
        youtube_timestamp_url=youtube_timestamp_url(video.youtube_video_id, chunk.start_ms),
        snippet=chunk.text[:420],
        score=round(score, 4),
        match_type=match_type,
        why=f"This chunk matched the query '{query}' through {match_type} search.",
    )
