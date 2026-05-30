from __future__ import annotations

from dataclasses import dataclass
import re

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import Q

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


def search_transcripts(query: str, search_type: str = "hybrid", limit: int = 20, filters: dict | None = None, user=None) -> list[dict]:
    filters = filters or {}
    if search_type == "keyword":
        results = _keyword(query, limit, filters, user)
    elif search_type == "semantic":
        results = _semantic(query, limit, filters, user)
    else:
        results = _hybrid(query, limit, filters, user)
    SearchQueryLog.objects.create(owner=user if getattr(user, "is_authenticated", False) else None, query_text=query, search_type=search_type, filters_json=filters, result_count=len(results))
    return [result.__dict__ for result in results]


def _base_queryset(filters: dict, user=None):
    qs = TranscriptChunk.objects.select_related("video", "transcript")
    if user is not None:
        qs = qs.filter(video__owner=user)
    channel = filters.get("channel")
    if channel:
        qs = qs.filter(video__channel_title__icontains=channel)
    return qs


def _keyword(query: str, limit: int, filters: dict, user=None) -> list[SearchResult]:
    search_query = SearchQuery(query, search_type="websearch")
    base = _base_queryset(filters, user)
    qs = list(
        base
        .annotate(rank=SearchRank("search_vector", search_query))
        .filter(Q(search_vector=search_query) | Q(text__icontains=query))
        .order_by("-rank")[: limit * 2]
    )
    results = []
    seen: set[str] = set()
    for chunk in qs:
        score = _keyword_score(chunk.text, query, float(getattr(chunk, "rank", 0) or 0))
        result = _to_result(chunk, score, "keyword", query)
        key = _dedupe_key(result)
        if key in seen:
            continue
        seen.add(key)
        results.append(result)
        if len(results) >= limit:
            break
    return results


def _semantic(query: str, limit: int, filters: dict, user=None) -> list[SearchResult]:
    from pgvector.django import CosineDistance

    vector = embed_texts([query])[0]
    qs = _base_queryset(filters, user).exclude(embedding__isnull=True).annotate(distance=CosineDistance("embedding", vector)).order_by("distance")[:limit]
    return [_to_result(chunk, max(0.0, 1.0 - float(chunk.distance or 1)), "semantic", query) for chunk in qs]


def _hybrid(query: str, limit: int, filters: dict, user=None) -> list[SearchResult]:
    combined: dict[str, SearchResult] = {}
    for result in _keyword(query, limit * 2, filters, user):
        combined[_dedupe_key(result)] = result
    for result in _semantic(query, limit * 2, filters, user):
        key = _dedupe_key(result)
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
    snippet = _snippet_for_query(chunk.text, query)
    start_ms, end_ms = _best_timestamp_for_query(chunk, query)
    return SearchResult(
        video_id=str(video.id),
        youtube_video_id=video.youtube_video_id,
        title=video.title,
        channel_title=video.channel_title,
        thumbnail_url=video.thumbnail_url,
        start_ms=start_ms,
        end_ms=end_ms,
        youtube_timestamp_url=youtube_timestamp_url(video.youtube_video_id, start_ms),
        snippet=snippet,
        score=round(score, 4),
        match_type=match_type,
        why=_why(chunk.text, query, match_type),
    )


def _dedupe_key(result: SearchResult) -> str:
    return f"{result.video_id}:{result.start_ms // 15000}:{_normalize(result.snippet)[:80]}"


def _snippet_for_query(text: str, query: str, max_chars: int = 520) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= max_chars:
        return clean
    terms = [term for term in re.findall(r"\w+", query.lower()) if len(term) > 2]
    lower = clean.lower()
    hit = min((lower.find(term) for term in terms if lower.find(term) >= 0), default=-1)
    if hit < 0:
        return clean[: max_chars - 1].rstrip() + "..."
    start = max(0, hit - max_chars // 3)
    end = min(len(clean), start + max_chars)
    start = max(0, end - max_chars)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(clean) else ""
    return f"{prefix}{clean[start:end].strip()}{suffix}"


def _why(text: str, query: str, match_type: str) -> str:
    terms = [term for term in re.findall(r"\w+", query.lower()) if len(term) > 2]
    matched = [term for term in terms if term in text.lower()]
    if matched:
        return f"Matched transcript terms: {', '.join(matched[:5])}."
    if match_type == "semantic":
        return "Matched by semantic similarity to the query."
    return f"Matched through {match_type} search."


def _normalize(text: str) -> str:
    return re.sub(r"\W+", " ", text).lower().strip()


def _keyword_score(text: str, query: str, rank: float) -> float:
    normalized_text = _normalize(text)
    normalized_query = _normalize(query)
    terms = [term for term in normalized_query.split() if len(term) > 2]
    score = min(0.95, rank * 12)
    if normalized_query and normalized_query in normalized_text:
        score = max(score, 1.0)
    elif terms:
        matched = sum(1 for term in terms if term in normalized_text)
        if matched:
            score = max(score, 0.35 + 0.5 * (matched / len(terms)))
    return round(max(score, 0.01), 4)


def _best_timestamp_for_query(chunk, query: str) -> tuple[int, int]:
    normalized_query = _normalize(query)
    terms = [term for term in normalized_query.split() if len(term) > 2]
    segments = chunk.transcript.segments.filter(start_ms__gte=chunk.start_ms, end_ms__lte=chunk.end_ms).order_by("segment_index")
    best_segment = None
    best_score = 0
    for segment in segments:
        normalized_text = _normalize(segment.text)
        score = 0
        if normalized_query and normalized_query in normalized_text:
            score += 10
        score += sum(1 for term in terms if term in normalized_text)
        if score > best_score:
            best_segment = segment
            best_score = score
    if best_segment:
        return best_segment.start_ms, best_segment.end_ms
    return chunk.start_ms, chunk.end_ms
