from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from pgvector.django import HnswIndex, VectorField


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Video(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="videos", blank=True, null=True)
    youtube_video_id = models.CharField(max_length=32)
    source_url = models.URLField()
    canonical_url = models.URLField()
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    channel_id = models.CharField(max_length=128, blank=True, null=True)
    channel_title = models.CharField(max_length=255, blank=True, null=True)
    thumbnail_url = models.URLField(blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(blank=True, null=True)
    published_at = models.DateTimeField(blank=True, null=True)
    view_count = models.BigIntegerField(blank=True, null=True)
    like_count = models.BigIntegerField(blank=True, null=True)
    comment_count = models.BigIntegerField(blank=True, null=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return self.title or self.youtube_video_id

    class Meta:
        constraints = [models.UniqueConstraint(fields=["owner", "youtube_video_id"], name="unique_owner_youtube_video")]


class Playlist(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="playlists", blank=True, null=True)
    youtube_playlist_id = models.CharField(max_length=128, blank=True, null=True)
    source_url = models.URLField()
    title = models.CharField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    channel_title = models.CharField(max_length=255, blank=True, null=True)
    metadata_json = models.JSONField(default=dict, blank=True)


class PlaylistVideo(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name="playlist_videos")
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="playlist_videos")
    position = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["playlist", "video"], name="unique_playlist_video")]


class IngestBatch(TimeStampedModel):
    class InputType(models.TextChoices):
        SINGLE_URL = "single_url"
        URL_LIST = "url_list"
        PLAYLIST = "playlist"

    class Status(models.TextChoices):
        QUEUED = "queued"
        RUNNING = "running"
        COMPLETED = "completed"
        PARTIAL_FAILED = "partial_failed"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ingest_batches", blank=True, null=True)
    input_text = models.TextField()
    input_type = models.CharField(max_length=32, choices=InputType.choices)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.QUEUED)
    total_count = models.PositiveIntegerField(default=0)
    completed_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)


class IngestJob(TimeStampedModel):
    class Status(models.TextChoices):
        QUEUED = "queued"
        RESOLVING = "resolving"
        METADATA_FETCHED = "metadata_fetched"
        TRANSCRIPT_FETCHING = "transcript_fetching"
        TRANSCRIBING = "transcribing"
        NORMALIZING = "normalizing"
        CHUNKING = "chunking"
        EMBEDDING = "embedding"
        SUMMARIZING = "summarizing"
        INDEXED = "indexed"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ingest_jobs", blank=True, null=True)
    batch = models.ForeignKey(IngestBatch, on_delete=models.CASCADE, related_name="jobs", blank=True, null=True)
    video = models.ForeignKey(Video, on_delete=models.SET_NULL, related_name="ingest_jobs", blank=True, null=True)
    source_url = models.URLField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.QUEUED)
    current_step = models.CharField(max_length=128, blank=True)
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)


class Transcript(TimeStampedModel):
    class SourceType(models.TextChoices):
        YOUTUBE_MANUAL = "youtube_manual_caption"
        YOUTUBE_AUTO = "youtube_auto_caption"
        YTDLP_MANUAL = "yt_dlp_manual_subtitle"
        YTDLP_AUTO = "yt_dlp_auto_subtitle"
        ASR_OPENAI = "asr_openai"
        ASR_LOCAL = "asr_local"
        MANUAL_UPLOAD = "manual_upload"

    class RawFormat(models.TextChoices):
        VTT = "vtt"
        SRT = "srt"
        JSON = "json"
        PLAIN_TEXT = "plain_text"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video = models.OneToOneField(Video, on_delete=models.CASCADE, related_name="transcript")
    language_code = models.CharField(max_length=16, default="en")
    source_type = models.CharField(max_length=64, choices=SourceType.choices)
    raw_text = models.TextField()
    raw_format = models.CharField(max_length=32, choices=RawFormat.choices)
    confidence = models.FloatField(blank=True, null=True)


class TranscriptSegment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transcript = models.ForeignKey(Transcript, on_delete=models.CASCADE, related_name="segments")
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="transcript_segments")
    start_ms = models.PositiveIntegerField(db_index=True)
    end_ms = models.PositiveIntegerField(db_index=True)
    text = models.TextField()
    segment_index = models.PositiveIntegerField()
    confidence = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["video", "start_ms"])]
        ordering = ["segment_index"]


class TranscriptChunk(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="transcript_chunks")
    transcript = models.ForeignKey(Transcript, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    start_ms = models.PositiveIntegerField(db_index=True)
    end_ms = models.PositiveIntegerField(db_index=True)
    text = models.TextField()
    token_count = models.PositiveIntegerField(blank=True, null=True)
    search_vector = SearchVectorField(blank=True, null=True)
    embedding = VectorField(dimensions=1536, blank=True, null=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["transcript", "chunk_index"], name="unique_transcript_chunk")]
        indexes = [
            models.Index(fields=["video", "start_ms"]),
            GinIndex(fields=["search_vector"], name="chunk_search_vector_gin"),
            HnswIndex(name="chunk_embedding_hnsw", fields=["embedding"], m=16, ef_construction=64, opclasses=["vector_cosine_ops"]),
        ]


class VideoSummary(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video = models.OneToOneField(Video, on_delete=models.CASCADE, related_name="summary")
    short_summary = models.TextField()
    detailed_summary = models.TextField(blank=True)
    key_points = models.JSONField(default=list, blank=True)
    topics = models.JSONField(default=list, blank=True)
    important_quotes = models.JSONField(default=list, blank=True)
    action_items = models.JSONField(default=list, blank=True)
    controversies = models.JSONField(default=list, blank=True)
    glossary = models.JSONField(default=list, blank=True)
    generated_by = models.CharField(max_length=128, blank=True)


class ViralMomentCandidate(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="viral_moments")
    start_ms = models.PositiveIntegerField()
    end_ms = models.PositiveIntegerField()
    hook = models.TextField()
    quote = models.TextField()
    reason = models.TextField()
    score = models.FloatField()
    suggested_title = models.TextField(blank=True, null=True)
    suggested_caption = models.TextField(blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        indexes = [models.Index(fields=["video", "-score"])]


class SearchQueryLog(models.Model):
    class SearchType(models.TextChoices):
        KEYWORD = "keyword"
        SEMANTIC = "semantic"
        HYBRID = "hybrid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_logs", blank=True, null=True)
    query_text = models.TextField()
    search_type = models.CharField(max_length=16, choices=SearchType.choices)
    filters_json = models.JSONField(default=dict, blank=True)
    result_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
