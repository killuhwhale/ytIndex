from __future__ import annotations

from django.contrib.postgres.search import SearchVector
from django.db import transaction
from django.utils import timezone

from config.celery import app

from .models import IngestBatch, IngestJob, Transcript, TranscriptChunk, TranscriptSegment, Video, VideoSummary, ViralMomentCandidate
from .services.chunker import chunk_segments
from .services.embeddings import embed_texts
from .services.metadata_provider import fetch_video_metadata
from .services.summarizer import summarize_transcript
from .services.transcript_normalizer import normalize_transcript
from .services.transcript_providers.manual_provider import ManualTranscriptProvider
from .services.transcript_providers.youtube_api_provider import YouTubeApiCaptionProvider
from .services.transcript_providers.ytdlp_subtitle_provider import YtDlpSubtitleProvider
from .services.viral_moments import generate_viral_candidates
from .services.youtube_url_parser import parse_youtube_url


@app.task
def ingest_job(job_id: str, context: dict | None = None) -> None:
    context = context or {}
    job = IngestJob.objects.select_related("batch", "owner").get(id=job_id)
    job.started_at = timezone.now()
    _set_status(job, IngestJob.Status.RESOLVING, "Parsing YouTube URL")

    try:
        parsed = parse_youtube_url(job.source_url)
        if parsed.type != "video":
            raise ValueError("Playlist expansion is represented at batch creation; job URLs must be videos.")
        metadata = fetch_video_metadata(parsed, job.source_url)
        video, _ = Video.objects.update_or_create(
            owner=job.owner,
            youtube_video_id=metadata.youtube_video_id,
            defaults={
                "source_url": metadata.source_url,
                "canonical_url": metadata.canonical_url,
                "title": metadata.title,
                "description": metadata.description,
                "channel_id": metadata.channel_id,
                "channel_title": metadata.channel_title,
                "thumbnail_url": metadata.thumbnail_url,
                "duration_seconds": metadata.duration_seconds,
                "metadata_json": metadata.metadata_json or {},
            },
        )
        job.video = video
        _set_status(job, IngestJob.Status.METADATA_FETCHED, "Metadata fetched")

        if hasattr(video, "transcript") and not context.get("force_refresh"):
            _set_status(job, IngestJob.Status.INDEXED, "Already indexed")
            _finish_job(job)
            return

        _set_status(job, IngestJob.Status.TRANSCRIPT_FETCHING, "Fetching transcript")
        fetch_result = _fetch_transcript(video, context)

        _set_status(job, IngestJob.Status.NORMALIZING, "Normalizing transcript")
        normalized = normalize_transcript(fetch_result.raw_text, fetch_result.raw_format)
        if not normalized:
            raise RuntimeError("Transcript provider returned no timestamped text.")

        with transaction.atomic():
            transcript, _ = Transcript.objects.update_or_create(
                video=video,
                defaults={
                    "language_code": fetch_result.language_code,
                    "source_type": fetch_result.source_type,
                    "raw_format": fetch_result.raw_format,
                    "raw_text": fetch_result.raw_text,
                },
            )
            TranscriptSegment.objects.filter(video=video).delete()
            TranscriptSegment.objects.bulk_create(
                [
                    TranscriptSegment(
                        transcript=transcript,
                        video=video,
                        start_ms=segment.start_ms,
                        end_ms=segment.end_ms,
                        text=segment.text,
                        segment_index=index,
                        confidence=segment.confidence,
                    )
                    for index, segment in enumerate(normalized)
                ]
            )

        _set_status(job, IngestJob.Status.CHUNKING, "Chunking transcript")
        segment_rows = list(TranscriptSegment.objects.filter(video=video).order_by("segment_index"))
        chunk_data = chunk_segments(segment_rows, min_tokens=350, max_tokens=850, overlap_tokens=90)
        TranscriptChunk.objects.filter(video=video).delete()
        chunks = TranscriptChunk.objects.bulk_create(
            [
                TranscriptChunk(
                    video=video,
                    transcript=transcript,
                    chunk_index=chunk.chunk_index,
                    start_ms=chunk.start_ms,
                    end_ms=chunk.end_ms,
                    text=chunk.text,
                    token_count=chunk.token_count,
                )
                for chunk in chunk_data
            ]
        )
        TranscriptChunk.objects.filter(video=video).update(search_vector=SearchVector("text", config="english"))

        _set_status(job, IngestJob.Status.EMBEDDING, "Embedding chunks")
        vectors = embed_texts([chunk.text for chunk in chunks])
        for chunk, vector in zip(chunks, vectors, strict=False):
            chunk.embedding = vector
        TranscriptChunk.objects.bulk_update(chunks, ["embedding"])

        _set_status(job, IngestJob.Status.SUMMARIZING, "Summarizing video")
        summary_data = summarize_transcript(video, chunks)
        VideoSummary.objects.update_or_create(video=video, defaults=summary_data)

        _set_status(job, IngestJob.Status.INDEXED, "Indexed")
        _finish_job(job)
    except Exception as exc:
        job.status = IngestJob.Status.FAILED
        job.current_step = "Failed"
        job.error_message = str(exc)
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "current_step", "error_message", "finished_at", "updated_at"])
    finally:
        _update_batch(job.batch_id)


@app.task
def generate_viral_moments(video_id: str) -> int:
    video = Video.objects.get(id=video_id)
    segments = list(video.transcript_segments.order_by("segment_index"))
    candidates = generate_viral_candidates(video, segments)
    ViralMomentCandidate.objects.filter(video=video).delete()
    ViralMomentCandidate.objects.bulk_create([ViralMomentCandidate(video=video, **candidate) for candidate in candidates])
    return len(candidates)


def _fetch_transcript(video: Video, context: dict):
    providers = [ManualTranscriptProvider(), YouTubeApiCaptionProvider(), YtDlpSubtitleProvider()]
    for provider in providers:
        if provider.can_handle(video, context):
            return provider.fetch(video, context)
    raise RuntimeError(
        "No transcript provider could handle this video. Provide manual_transcript, enable permitted yt-dlp subtitles, or enable owned-content ASR fallback."
    )


def _set_status(job: IngestJob, status: str, step: str) -> None:
    job.status = status
    job.current_step = step
    job.save(update_fields=["status", "current_step", "video", "started_at", "updated_at"])


def _finish_job(job: IngestJob) -> None:
    job.finished_at = timezone.now()
    job.save(update_fields=["finished_at", "updated_at"])


def _update_batch(batch_id) -> None:
    if not batch_id:
        return
    batch = IngestBatch.objects.get(id=batch_id)
    jobs = list(batch.jobs.all())
    batch.total_count = len(jobs)
    batch.completed_count = sum(1 for job in jobs if job.status == IngestJob.Status.INDEXED)
    batch.failed_count = sum(1 for job in jobs if job.status == IngestJob.Status.FAILED)
    if batch.completed_count + batch.failed_count < batch.total_count:
        batch.status = IngestBatch.Status.RUNNING
    elif batch.failed_count and batch.completed_count:
        batch.status = IngestBatch.Status.PARTIAL_FAILED
    elif batch.failed_count:
        batch.status = IngestBatch.Status.FAILED
    else:
        batch.status = IngestBatch.Status.COMPLETED
    batch.save()
