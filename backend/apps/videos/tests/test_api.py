import pytest
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import SearchVector
from django.test import override_settings
from rest_framework.test import APIClient

from apps.videos.models import IngestBatch, IngestJob, Transcript, TranscriptChunk, TranscriptSegment, Video
from apps.videos.services.search import search_transcripts


def make_user(email: str = "andayac@gmail.com"):
    return get_user_model().objects.create_user(username=email, email=email, password="test-pass-12345")


def authenticated_client(user=None):
    user = user or make_user()
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.mark.django_db
def test_ingest_rejects_bad_url():
    client, _ = authenticated_client()
    response = client.post("/api/ingest/", {"input": "https://example.com/nope"}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_search_requires_query():
    client, _ = authenticated_client()
    response = client.post("/api/search/", {"query": ""}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
@override_settings(AUTH_ALLOWED_EMAILS={"andayac@gmail.com"})
def test_register_allows_allowlisted_email():
    response = APIClient().post(
        "/api/auth/register/",
        {"email": "andayac@gmail.com", "password": "test-pass-12345"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["authenticated"] is True
    assert response.data["user"]["email"] == "andayac@gmail.com"


@pytest.mark.django_db
@override_settings(AUTH_ALLOWED_EMAILS={"andayac@gmail.com"})
def test_register_rejects_unlisted_email():
    response = APIClient().post(
        "/api/auth/register/",
        {"email": "someone@example.com", "password": "test-pass-12345"},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_video_list_only_returns_current_users_videos():
    user = make_user("owner@example.com")
    other_user = make_user("other@example.com")
    own_video = create_video(user, "same-id", "Own video")
    create_video(other_user, "same-id", "Other video")

    client, _ = authenticated_client(user)
    response = client.get("/api/videos/")

    assert response.status_code == 200
    assert [item["id"] for item in response.data] == [str(own_video.id)]


@pytest.mark.django_db
def test_video_detail_does_not_expose_other_users_video():
    user = make_user("owner@example.com")
    other_user = make_user("other@example.com")
    other_video = create_video(other_user, "other-id", "Other video")

    client, _ = authenticated_client(user)
    response = client.get(f"/api/videos/{other_video.id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_ingest_batch_detail_does_not_expose_other_users_batch():
    user = make_user("owner@example.com")
    other_user = make_user("other@example.com")
    batch = IngestBatch.objects.create(owner=other_user, input_text="https://youtu.be/abc123", input_type=IngestBatch.InputType.SINGLE_URL)
    IngestJob.objects.create(owner=other_user, batch=batch, source_url="https://youtu.be/abc123")

    client, _ = authenticated_client(user)
    response = client.get(f"/api/ingest/batches/{batch.id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_keyword_search_only_returns_current_users_chunks():
    user = make_user("owner@example.com")
    other_user = make_user("other@example.com")
    own_video = create_video(user, "own-id", "Own video")
    other_video = create_video(other_user, "other-id", "Other video")
    create_transcript_chunk(own_video, "private search phrase from owner")
    create_transcript_chunk(other_video, "private search phrase from someone else")

    results = search_transcripts("private", search_type="keyword", user=user)

    assert len(results) == 1
    assert results[0]["video_id"] == str(own_video.id)


@pytest.mark.django_db
def test_keyword_search_exact_match_uses_matching_segment_timestamp_and_nonzero_score():
    user = make_user("owner@example.com")
    video = create_video(user, "own-id", "Own video")
    transcript = Transcript.objects.create(
        video=video,
        language_code="en",
        source_type=Transcript.SourceType.MANUAL_UPLOAD,
        raw_text="opening text target phrase appears later",
        raw_format=Transcript.RawFormat.PLAIN_TEXT,
    )
    TranscriptSegment.objects.create(transcript=transcript, video=video, start_ms=0, end_ms=5000, text="opening text", segment_index=0)
    TranscriptSegment.objects.create(transcript=transcript, video=video, start_ms=45000, end_ms=51000, text="target phrase appears later", segment_index=1)
    chunk = TranscriptChunk.objects.create(
        video=video,
        transcript=transcript,
        chunk_index=0,
        start_ms=0,
        end_ms=51000,
        text="opening text target phrase appears later",
        token_count=7,
    )
    TranscriptChunk.objects.filter(pk=chunk.pk).update(search_vector=SearchVector("text", config="english"))

    results = search_transcripts("target phrase", search_type="keyword", user=user)

    assert results[0]["score"] > 0
    assert results[0]["start_ms"] == 45000
    assert results[0]["youtube_timestamp_url"].endswith("&t=45s")


def create_video(owner, youtube_video_id: str, title: str) -> Video:
    return Video.objects.create(
        owner=owner,
        youtube_video_id=youtube_video_id,
        source_url=f"https://youtube.com/watch?v={youtube_video_id}",
        canonical_url=f"https://youtube.com/watch?v={youtube_video_id}",
        title=title,
    )


def create_transcript_chunk(video: Video, text: str) -> TranscriptChunk:
    transcript = Transcript.objects.create(
        video=video,
        language_code="en",
        source_type=Transcript.SourceType.MANUAL_UPLOAD,
        raw_text=text,
        raw_format=Transcript.RawFormat.PLAIN_TEXT,
    )
    chunk = TranscriptChunk.objects.create(
        video=video,
        transcript=transcript,
        chunk_index=0,
        start_ms=0,
        end_ms=1000,
        text=text,
        token_count=len(text.split()),
    )
    TranscriptSegment.objects.create(transcript=transcript, video=video, start_ms=0, end_ms=1000, text=text, segment_index=0)
    TranscriptChunk.objects.filter(pk=chunk.pk).update(search_vector=SearchVector("text", config="english"))
    chunk.refresh_from_db()
    return chunk
