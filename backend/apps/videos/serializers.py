from __future__ import annotations

from rest_framework import serializers

from .models import IngestBatch, IngestJob, TranscriptSegment, Video, VideoSummary, ViralMomentCandidate
from .services.youtube_url_parser import youtube_timestamp_url


class IngestJobSerializer(serializers.ModelSerializer):
    video_id = serializers.UUIDField(source="video.id", read_only=True)

    class Meta:
        model = IngestJob
        fields = ["id", "batch", "video_id", "source_url", "status", "current_step", "error_message", "retry_count", "started_at", "finished_at", "created_at", "updated_at"]


class IngestBatchSerializer(serializers.ModelSerializer):
    jobs = IngestJobSerializer(many=True, read_only=True)

    class Meta:
        model = IngestBatch
        fields = ["id", "input_text", "input_type", "status", "total_count", "completed_count", "failed_count", "error_message", "jobs", "created_at", "updated_at"]


class VideoSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoSummary
        fields = ["short_summary", "detailed_summary", "key_points", "topics", "important_quotes", "action_items", "controversies", "glossary", "generated_by", "created_at", "updated_at"]


class VideoSerializer(serializers.ModelSerializer):
    summary = VideoSummarySerializer(read_only=True)

    class Meta:
        model = Video
        fields = ["id", "youtube_video_id", "source_url", "canonical_url", "title", "description", "channel_id", "channel_title", "thumbnail_url", "duration_seconds", "published_at", "view_count", "like_count", "comment_count", "metadata_json", "summary", "created_at", "updated_at"]


class TranscriptSegmentSerializer(serializers.ModelSerializer):
    youtube_timestamp_url = serializers.SerializerMethodField()

    class Meta:
        model = TranscriptSegment
        fields = ["id", "start_ms", "end_ms", "text", "segment_index", "confidence", "youtube_timestamp_url"]

    def get_youtube_timestamp_url(self, obj) -> str:
        return youtube_timestamp_url(obj.video.youtube_video_id, obj.start_ms)


class ViralMomentSerializer(serializers.ModelSerializer):
    youtube_timestamp_url = serializers.SerializerMethodField()

    class Meta:
        model = ViralMomentCandidate
        fields = ["id", "start_ms", "end_ms", "hook", "quote", "reason", "score", "suggested_title", "suggested_caption", "tags", "youtube_timestamp_url", "created_at"]

    def get_youtube_timestamp_url(self, obj) -> str:
        return youtube_timestamp_url(obj.video.youtube_video_id, obj.start_ms)
