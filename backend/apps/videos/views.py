from __future__ import annotations

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView, RetrieveDestroyAPIView

from .models import IngestBatch, IngestJob, Video, ViralMomentCandidate
from .serializers import (
    CurrentUserSerializer,
    IngestBatchSerializer,
    IngestJobSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    TranscriptSegmentSerializer,
    VideoSerializer,
    VideoSummarySerializer,
    ViralMomentSerializer,
)
from .services.metadata_provider import fetch_playlist_video_urls
from .services.search import search_transcripts
from .services.youtube_url_parser import YouTubeUrlError, parse_youtube_url, split_input_urls
from .tasks import generate_viral_moments, ingest_job


User = get_user_model()


def auth_response(request, user=None, status_code=status.HTTP_200_OK):
    user = user or request.user
    data = {
        "authenticated": bool(user and user.is_authenticated),
        "csrf_token": get_token(request),
        "user": CurrentUserSerializer(user).data if user and user.is_authenticated else None,
    }
    return Response(data, status=status_code)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CurrentUserView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return auth_response(request)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user)
        return auth_response(request, user, status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        return auth_response(request, user)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"authenticated": False, "csrf_token": get_token(request), "user": None})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        if email in settings.AUTH_ALLOWED_EMAILS:
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_url = f"{settings.FRONTEND_APP_URL.rstrip('/')}/reset-password/confirm?uid={uid}&token={token}"
                send_mail(
                    "Reset your VideoRecall password",
                    f"Use this link to reset your VideoRecall password:\n\n{reset_url}\n\nIf you did not request this, you can ignore this email.",
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
        return Response({"detail": "If an approved account exists for that email, a password reset link has been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password has been reset."})


class IngestCreateView(APIView):
    throttle_scope = "ingest"

    def post(self, request):
        input_text = request.data.get("input", "")
        force_refresh = bool(request.data.get("force_refresh", False))
        manual_transcript = request.data.get("manual_transcript")
        urls = split_input_urls(input_text)
        if not urls:
            return Response({"detail": "Input must contain at least one YouTube URL."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parsed = [parse_youtube_url(url) for url in urls]
        except YouTubeUrlError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        input_type = IngestBatch.InputType.URL_LIST if len(urls) > 1 else IngestBatch.InputType.SINGLE_URL
        if parsed[0].type == "playlist" and len(parsed) == 1:
            input_type = IngestBatch.InputType.PLAYLIST
            try:
                urls = fetch_playlist_video_urls(parsed[0].playlist_id)
                parsed = [parse_youtube_url(url) for url in urls]
            except RuntimeError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        batch = IngestBatch.objects.create(
            owner=request.user,
            input_text=input_text,
            input_type=input_type,
            status=IngestBatch.Status.RUNNING,
            total_count=len(urls),
        )
        jobs = [IngestJob.objects.create(owner=request.user, batch=batch, source_url=item.canonical_url) for item in parsed if item.type == "video"]
        context = {
            "force_refresh": force_refresh,
            "owned_content": bool(request.data.get("owned_content", False)),
            "allow_ytdlp": bool(request.data.get("allow_ytdlp", True)),
        }
        if manual_transcript:
            context["manual_transcript"] = manual_transcript
        for job in jobs:
            ingest_job.delay(str(job.id), context)
        return Response({"batch_id": str(batch.id), "job_ids": [str(job.id) for job in jobs]}, status=status.HTTP_201_CREATED)


class IngestBatchDetailView(RetrieveAPIView):
    serializer_class = IngestBatchSerializer

    def get_queryset(self):
        return IngestBatch.objects.filter(owner=self.request.user).prefetch_related("jobs")


class IngestJobDetailView(RetrieveAPIView):
    serializer_class = IngestJobSerializer

    def get_queryset(self):
        return IngestJob.objects.filter(owner=self.request.user)


class RetryIngestJobView(APIView):
    def post(self, request, pk):
        job = get_object_or_404(IngestJob, pk=pk, owner=request.user)
        job.retry_count += 1
        job.status = IngestJob.Status.QUEUED
        job.error_message = None
        job.save()
        ingest_job.delay(str(job.id), {"force_refresh": request.data.get("force_refresh", False)})
        return Response(IngestJobSerializer(job).data)


class VideoListView(ListAPIView):
    serializer_class = VideoSerializer

    def get_queryset(self):
        return Video.objects.filter(owner=self.request.user).order_by("-created_at")[:50]


class VideoDetailView(RetrieveDestroyAPIView):
    serializer_class = VideoSerializer

    def get_queryset(self):
        return Video.objects.filter(owner=self.request.user).select_related("summary")


class VideoTranscriptView(APIView):
    def get(self, request, pk):
        video = get_object_or_404(Video, pk=pk, owner=request.user)
        return Response({"video_id": str(video.id), "segments": TranscriptSegmentSerializer(video.transcript_segments.order_by("segment_index"), many=True).data})


class VideoSummaryView(APIView):
    def get(self, request, pk):
        video = get_object_or_404(Video, pk=pk, owner=request.user)
        if not hasattr(video, "summary"):
            return Response({"detail": "Summary has not been generated."}, status=status.HTTP_404_NOT_FOUND)
        return Response(VideoSummarySerializer(video.summary).data)


class GenerateSummaryView(APIView):
    def post(self, request, pk):
        video = get_object_or_404(Video, pk=pk, owner=request.user)
        latest = video.ingest_jobs.order_by("-created_at").first()
        if not latest:
            latest = IngestJob.objects.create(owner=request.user, batch=None, video=video, source_url=video.canonical_url)
        ingest_job.delay(str(latest.id), {"force_refresh": True})
        return Response({"job_id": str(latest.id)})


class ViralMomentsView(APIView):
    def get(self, request, pk):
        video = get_object_or_404(Video, pk=pk, owner=request.user)
        return Response({"results": ViralMomentSerializer(video.viral_moments.order_by("-score"), many=True).data})

    def post(self, request, pk):
        video = get_object_or_404(Video, pk=pk, owner=request.user)
        if not video.transcript_segments.exists():
            return Response({"detail": "Transcript is required before viral moments can be generated."}, status=status.HTTP_400_BAD_REQUEST)
        if request.query_params.get("sync") == "true":
            generate_viral_moments(str(video.id))
        else:
            generate_viral_moments.delay(str(video.id))
        return Response({"detail": "Viral moment generation started."})


class SearchView(APIView):
    def post(self, request):
        query = request.data.get("query", "").strip()
        if not query:
            return Response({"detail": "query is required."}, status=status.HTTP_400_BAD_REQUEST)
        results = search_transcripts(
            query=query,
            search_type=request.data.get("search_type", "hybrid"),
            limit=int(request.data.get("limit", 20)),
            filters=request.data.get("filters") or {},
            user=request.user,
        )
        return Response({"results": results})
