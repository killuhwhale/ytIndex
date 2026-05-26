from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView, RetrieveDestroyAPIView

from .models import IngestBatch, IngestJob, Video, ViralMomentCandidate
from .serializers import IngestBatchSerializer, IngestJobSerializer, TranscriptSegmentSerializer, VideoSerializer, VideoSummarySerializer, ViralMomentSerializer
from .services.metadata_provider import fetch_playlist_video_urls
from .services.search import search_transcripts
from .services.youtube_url_parser import YouTubeUrlError, parse_youtube_url, split_input_urls
from .tasks import generate_viral_moments, ingest_job


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

        batch = IngestBatch.objects.create(input_text=input_text, input_type=input_type, status=IngestBatch.Status.RUNNING, total_count=len(urls))
        jobs = [IngestJob.objects.create(batch=batch, source_url=item.canonical_url) for item in parsed if item.type == "video"]
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
    queryset = IngestBatch.objects.prefetch_related("jobs")
    serializer_class = IngestBatchSerializer


class IngestJobDetailView(RetrieveAPIView):
    queryset = IngestJob.objects.all()
    serializer_class = IngestJobSerializer


class RetryIngestJobView(APIView):
    def post(self, request, pk):
        job = IngestJob.objects.get(pk=pk)
        job.retry_count += 1
        job.status = IngestJob.Status.QUEUED
        job.error_message = None
        job.save()
        ingest_job.delay(str(job.id), {"force_refresh": request.data.get("force_refresh", False)})
        return Response(IngestJobSerializer(job).data)


class VideoListView(ListAPIView):
    serializer_class = VideoSerializer

    def get_queryset(self):
        return Video.objects.order_by("-created_at")[:50]


class VideoDetailView(RetrieveDestroyAPIView):
    queryset = Video.objects.select_related("summary")
    serializer_class = VideoSerializer


class VideoTranscriptView(APIView):
    def get(self, request, pk):
        video = Video.objects.get(pk=pk)
        return Response({"video_id": str(video.id), "segments": TranscriptSegmentSerializer(video.transcript_segments.order_by("segment_index"), many=True).data})


class VideoSummaryView(APIView):
    def get(self, request, pk):
        video = Video.objects.get(pk=pk)
        if not hasattr(video, "summary"):
            return Response({"detail": "Summary has not been generated."}, status=status.HTTP_404_NOT_FOUND)
        return Response(VideoSummarySerializer(video.summary).data)


class GenerateSummaryView(APIView):
    def post(self, request, pk):
        video = Video.objects.get(pk=pk)
        latest = video.ingest_jobs.order_by("-created_at").first()
        if not latest:
            latest = IngestJob.objects.create(video=video, source_url=video.canonical_url)
        ingest_job.delay(str(latest.id), {"force_refresh": True})
        return Response({"job_id": str(latest.id)})


class ViralMomentsView(APIView):
    def get(self, request, pk):
        video = Video.objects.get(pk=pk)
        return Response({"results": ViralMomentSerializer(video.viral_moments.order_by("-score"), many=True).data})

    def post(self, request, pk):
        video = Video.objects.get(pk=pk)
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
        )
        return Response({"results": results})
