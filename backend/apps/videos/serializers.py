from __future__ import annotations

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from .models import IngestBatch, IngestJob, TranscriptSegment, Video, VideoSummary, ViralMomentCandidate
from .services.youtube_url_parser import youtube_timestamp_url


User = get_user_model()


class CurrentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "first_name", "last_name"]


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value: str) -> str:
        email = value.lower()
        if email not in settings.AUTH_ALLOWED_EMAILS:
            raise serializers.ValidationError("This email is not approved for access.")
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise serializers.ValidationError("An account already exists for this email.")
        return email

    def validate_password(self, value: str) -> str:
        password_validation.validate_password(value)
        return value

    def create(self, validated_data):
        email = validated_data["email"]
        return User.objects.create_user(username=email, email=email, password=validated_data["password"])


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        email = attrs["email"].lower()
        user = authenticate(username=email, password=attrs["password"])
        if user is None:
            raise serializers.ValidationError("Unable to log in with those credentials.")
        if not user.is_active:
            raise serializers.ValidationError("This account is disabled.")
        attrs["user"] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_password(self, value: str) -> str:
        password_validation.validate_password(value)
        return value

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("The password reset link is invalid.")
        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError("The password reset link is invalid or expired.")
        attrs["user"] = user
        return attrs


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
