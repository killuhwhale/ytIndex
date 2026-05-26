cat > AGENTS.md <<'EOF'
# AGENTS.md

## Project Name

VideoRecall

## Project Purpose

Build a full-stack web app for ingesting YouTube videos/playlists, retrieving or generating transcripts, summarizing videos, indexing transcripts, searching across transcript chunks, and identifying candidate viral moments.

The main user goal is to answer questions like:

- “What are the main points of this video?”
- “Which video talked about subject X?”
- “Where did someone mention topic Y?”
- “What moments from this old video could become viral short clips?”

Always preserve timestamp links back to the original YouTube video.

---

## Tech Stack

### Backend

Use:

- Python 3.12+
- Django
- Django REST Framework
- PostgreSQL
- pgvector
- Postgres full-text search
- Redis
- Celery
- Docker Compose
- OpenAI SDK for summaries, embeddings, and optional transcription
- yt-dlp only as a permitted transcript/subtitle provider

### Frontend

Use:

- React
- Vite
- TypeScript
- Tailwind CSS
- TanStack Query
- React Router
- Clean component-based UI

---

## Important Compliance Rules

Do not build features that bypass YouTube access controls, DRM, paywalls, authentication, or Terms of Service.

Do not assume YouTube Premium gives permission to bulk download, transcribe, or index videos.

Design transcript ingestion as a pluggable provider system:

1. Existing stored transcript
2. Official YouTube captions API only when authorized
3. yt-dlp subtitle/auto-subtitle extraction only where permitted
4. ASR fallback only for user-owned, licensed, or otherwise permitted media
5. Manual transcript upload

Never hardcode user credentials, browser cookies, session tokens, or API keys.

Do not download full video/audio unless the app is explicitly configured for user-owned or licensed content.

---

## Architecture Expectations

Keep business logic out of views.

Use this structure:

```text
backend/
  config/
  apps/
    videos/
      models.py
      serializers.py
      views.py
      urls.py
      tasks.py
      services/
        youtube_url_parser.py
        metadata_provider.py
        transcript_providers/
          base.py
          youtube_api_provider.py
          ytdlp_subtitle_provider.py
          asr_provider.py
          manual_provider.py
        transcript_normalizer.py
        chunker.py
        embeddings.py
        summarizer.py
        search.py
        viral_moments.py

Frontend:

frontend/
  src/
    api/
    components/
    pages/
    main.tsx
Core Backend Models

Implement models for:

Video
Playlist
PlaylistVideo
IngestBatch
IngestJob
Transcript
TranscriptSegment
TranscriptChunk
VideoSummary
ViralMomentCandidate
SearchQueryLog

Use UUID primary keys unless there is a strong reason not to.

Important indexes:

Unique index on Video.youtube_video_id
Index transcript segments by video_id and start_ms
Index transcript chunks by video_id and start_ms
GIN full-text index for transcript chunks
pgvector index for transcript chunk embeddings
Ingestion Rules

Every ingest should run through Celery.

A single submitted URL/list/playlist creates an IngestBatch.

Each video creates an IngestJob.

Jobs should be idempotent.

Do not duplicate already-indexed videos unless force_refresh=true.

Each job should move through clear statuses:

queued
resolving
metadata_fetched
transcript_fetching
transcribing
normalizing
chunking
embedding
summarizing
indexed
failed

Failed jobs should preserve error messages and be retryable.

Transcript Rules

Normalize every transcript into timestamped segments.

Each TranscriptSegment must have:

start_ms
end_ms
text
segment_index

Do not lose timestamps.

All search results must be able to link back to the original YouTube timestamp.

Timestamp URL format:

https://youtube.com/watch?v=VIDEO_ID&t=123s
Chunking Rules

Chunk transcript text into approximately 400-900 token chunks.

Use 50-100 token overlap.

Each chunk must preserve:

start_ms
end_ms
chunk_index
text
token_count

Generate:

Postgres full-text search vector
Embedding vector using pgvector

Avoid re-embedding unchanged chunks.

Search Rules

Implement three search modes:

Keyword search
Use Postgres full-text search.
Semantic search
Embed the user query and search pgvector.
Hybrid search
Combine keyword and semantic scores.

Hybrid search should:

Normalize scores
Deduplicate near-identical chunks
Diversify results so one video does not dominate
Return timestamp links
Return a short explanation of why each result matched

Search result objects should include:

video id
YouTube video id
title
channel title
thumbnail
transcript snippet
start timestamp
end timestamp
YouTube timestamp URL
score
match type
why this matched
Summary Rules

For every indexed video, generate:

Short summary
Detailed summary
Key points
Topics with timestamps
Important quotes with timestamps
Action items if present
Controversies/debates if present

For long videos, use map-reduce summarization:

Summarize transcript chunks
Combine chunk summaries
Produce final structured summary

Prefer structured JSON outputs from LLM calls.

Validate LLM outputs before saving.

Viral Moments Rules

Do not create downloadable clips in the MVP unless the source content is user-owned or licensed.

Instead, identify candidate moments with timestamps.

Each viral moment should include:

start_ms
end_ms
hook
quote
reason
score
suggested title
suggested caption
tags
YouTube timestamp link

Score windows based on:

hook strength
emotional intensity
novelty
clarity
usefulness
controversy
surprise
self-contained context
quotability
Frontend Rules

Build a clean dashboard with:

URL/list/playlist input
Ingest button
Recent batches
Recently indexed videos
Search box

Build pages for:

Dashboard
Batch detail
Video detail
Search

Video detail page should have tabs:

Summary
Transcript
Search within video
Viral moments

Every timestamp should be clickable.

Use TanStack Query for server state.

Keep components small and readable.

API Expectations

Implement endpoints similar to:

POST /api/ingest/
GET /api/ingest/batches/:id/
GET /api/ingest/jobs/:id/
POST /api/ingest/jobs/:id/retry/

GET /api/videos/
GET /api/videos/:id/
GET /api/videos/:id/transcript/
GET /api/videos/:id/summary/
POST /api/videos/:id/generate-summary/

POST /api/videos/:id/viral-moments/
GET /api/videos/:id/viral-moments/

POST /api/search/

Use predictable JSON responses.

Return useful errors.

Security Rules

Validate all submitted URLs.

Only allow recognized YouTube hostnames:

youtube.com
www.youtube.com
m.youtube.com
youtu.be
music.youtube.com, if intentionally supported

Prevent arbitrary URL fetching.

Never commit .env.

Provide .env.example.

Store secrets only in environment variables.

Add CORS config for the local Vite frontend.

Add basic rate limiting to ingest endpoints.

Local Development

Provide Docker Compose services for:

backend
frontend
postgres with pgvector
redis
celery worker

Add a README with:

setup
environment variables
migrations
running backend
running frontend
running Celery
ingesting a demo video
running tests

Useful commands should be added to a Makefile if appropriate:

make setup
make dev
make migrate
make test
make ingest-demo
Testing Expectations

Write tests for:

YouTube URL parsing
playlist URL parsing
VTT parsing
SRT parsing
transcript normalization
chunking timestamp preservation
duplicate video ingest
Celery task idempotency
search timestamp URL generation
keyword search
semantic search
hybrid search score merging
core API endpoints

Do not skip tests for the URL parser, transcript normalizer, chunker, or search service.

Coding Style

Use type hints.

Prefer small service functions.

Prefer explicit error handling.

Prefer clear status transitions.

Keep code easy to read.

Do not over-engineer the MVP.

When modifying existing code:

Inspect current structure first.
Reuse existing patterns.
Add tests for behavior changes.
Run relevant tests before finishing.
Implementation Priority

Phase 1:

Django/React project setup
Docker Compose
Models/migrations
URL parser
Single video ingest
Transcript provider interface
yt-dlp subtitle provider behind feature flag
Transcript normalization
Chunking
Postgres full-text search
Basic summaries
Basic frontend pages

Phase 2:

pgvector embeddings
Semantic search
Hybrid search
Playlist ingestion
Batch progress UI
Retry failed jobs

Phase 3:

Viral moment detection
ASR fallback
Better filters
Production hardening
Definition of Done

The MVP is done when:

A user can paste a YouTube URL.
The app creates an ingest job.
The app retrieves or accepts a transcript.
The transcript is normalized into timestamped segments.
The transcript is chunked and indexed.
The user can view a summary.
The user can search for a topic.
Search results link back to exact YouTube timestamps.
The user can generate viral moment candidates.
The full stack runs locally with Docker Compose.
