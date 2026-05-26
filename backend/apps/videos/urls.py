from django.urls import path

from . import views

urlpatterns = [
    path("ingest/", views.IngestCreateView.as_view(), name="ingest-create"),
    path("ingest/batches/<uuid:pk>/", views.IngestBatchDetailView.as_view(), name="ingest-batch-detail"),
    path("ingest/jobs/<uuid:pk>/", views.IngestJobDetailView.as_view(), name="ingest-job-detail"),
    path("ingest/jobs/<uuid:pk>/retry/", views.RetryIngestJobView.as_view(), name="ingest-job-retry"),
    path("videos/", views.VideoListView.as_view(), name="video-list"),
    path("videos/<uuid:pk>/", views.VideoDetailView.as_view(), name="video-detail"),
    path("videos/<uuid:pk>/transcript/", views.VideoTranscriptView.as_view(), name="video-transcript"),
    path("videos/<uuid:pk>/summary/", views.VideoSummaryView.as_view(), name="video-summary"),
    path("videos/<uuid:pk>/generate-summary/", views.GenerateSummaryView.as_view(), name="video-generate-summary"),
    path("videos/<uuid:pk>/viral-moments/", views.ViralMomentsView.as_view(), name="video-viral-moments"),
    path("search/", views.SearchView.as_view(), name="search"),
]
