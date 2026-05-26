# VideoRecall

VideoRecall is a local full-stack MVP for ingesting permitted YouTube transcripts, normalizing them into timestamped segments, summarizing videos, indexing transcript chunks, searching across indexed content, and suggesting viral-moment timestamps.

The app is intentionally compliance-first: it does not bypass YouTube access controls, DRM, paywalls, authentication, account restrictions, or Terms of Service. The easiest local demo path is to paste a YouTube URL and provide a manual transcript for content you are allowed to process.

## What You Can Demo

- Paste one YouTube URL or multiple URLs.
- Track ingest jobs and failures.
- Store a timestamped transcript.
- View a generated summary.
- Search transcript chunks with timestamp links.
- Generate transcript-only viral moment candidates.
- Use `yt-dlp` as the primary provider: subtitles first, then optional owned-content audio transcription.

## Requirements

- Docker Desktop or Docker Engine with Compose
- `make`
- Optional: OpenAI API key for real summaries and embeddings
- Optional: YouTube Data API key for playlist expansion and richer metadata

## Quick Start

From the repo root:

```bash
make setup
make migrate
make dev
```

Then open:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api
- Django admin: http://localhost:8000/admin

`make dev` stays running and streams logs for the backend, Celery worker, frontend, Postgres, and Redis.

## Makefile Commands

```bash
make setup
```

Copies `.env.example` to `.env` if needed and builds Docker images.

```bash
make migrate
```

Runs Django migrations against the Postgres container.

```bash
make dev
```

Starts the whole local stack.

```bash
make test
```

Runs the backend pytest suite inside Docker.

```bash
make ingest-demo
```

Creates an ingest job for a sample YouTube URL from the command line. By default this will only succeed if a transcript provider is configured, because the app does not scrape or download media automatically.

## Demo Flow 1: Manual Transcript Ingest

This is the safest demo because it does not require YouTube captions access, `yt-dlp`, or media downloads.

1. Start the app:

```bash
make setup
make migrate
make dev
```

2. Open http://localhost:5173.

3. Paste a YouTube URL in the first text box:

```text
https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

4. Paste a manual transcript in the second text box:

```text
Most people think the hard part is starting, but the truth is consistency wins.
The mistake is trying to make everything perfect before publishing.
I learned that small repeatable systems beat huge one-time efforts.
This is a concise teaching moment that can become a strong short clip.
```

5. Click `Start ingest`.

6. The app redirects to the batch page. Wait for the job to reach `indexed`.

7. Open the indexed video from the batch table.

8. Use the tabs:

- `summary`: view the generated local fallback summary.
- `transcript`: view timestamped segments and open YouTube timestamp links.
- `viral`: click `Generate moments` to create candidate short-form moments.

9. Open `Search` from the top nav and search:

```text
consistency
```

Use `hybrid`, `keyword`, or `semantic` mode.

## Demo Flow 2: Command-Line Ingest

Run:

```bash
docker compose run --rm backend python manage.py ingest_youtube_url \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --manual-transcript "The truth is consistency wins. The mistake is waiting for perfection."
```

Then search:

```bash
docker compose run --rm backend python manage.py search_transcripts "consistency"
```

For owned/licensed media where ASR fallback is allowed:

```bash
docker compose run --rm backend python manage.py ingest_youtube_url \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  --owned-content
```

## Optional: Use OpenAI

Edit `.env`:

```env
OPENAI_API_KEY=sk-...
OPENAI_SUMMARY_MODEL=gpt-4.1-mini
OPENAI_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe-2025-12-15
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

Restart:

```bash
make dev
```

Without `OPENAI_API_KEY`, the app uses deterministic local embeddings and simple extractive summaries so the demo still works.

## Optional: Enable yt-dlp Provider

Only enable this for videos where subtitle retrieval or owned-content audio processing is permitted by rights and terms.

Edit `.env`:

```env
ENABLE_YTDLP_PROVIDER=true
```

Restart the stack:

```bash
make dev
```

With only this flag enabled, the provider is subtitle-only and uses `--skip-download`. It does not download full video/audio.

## Optional: Fallback to Audio Transcription

If subtitles are unavailable, VideoRecall can use `yt-dlp` to extract audio and send it to OpenAI speech-to-text. This is disabled unless every required gate is enabled.

Edit `.env`:

```env
ENABLE_YTDLP_PROVIDER=true
ENABLE_ASR_PROVIDER=true
ALLOW_MEDIA_DOWNLOADS_FOR_OWNED_CONTENT=true
OPENAI_API_KEY=sk-...
OPENAI_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe-2025-12-15
```

Restart:

```bash
docker compose down
make dev
```

Then, in the ingest form, check:

```text
I own this media or have rights to download audio for transcription if subtitles are unavailable.
```

The provider order is:

1. Try manual subtitles with `yt-dlp --skip-download --write-subs`.
2. Try auto subtitles with `yt-dlp --skip-download --write-auto-subs`.
3. If allowed, extract audio with `yt-dlp -x --audio-format mp3`.
4. Transcribe with OpenAI speech-to-text.

This fallback downloads audio only into a temporary job directory. The temp file is deleted when the provider finishes. `gpt-4o-mini-transcribe` returns transcript text without segment timestamps through the transcription API, so ASR results are stored as one coarse transcript segment. Use `whisper-1` if you need segment timestamps from ASR.

## Optional: Playlist URLs

Playlist expansion requires a YouTube Data API key.

Edit `.env`:

```env
YOUTUBE_API_KEY=your-key
```

Then submit a playlist URL:

```text
https://www.youtube.com/playlist?list=PLAYLIST_ID
```

The backend expands the playlist into one ingest job per video.

## API Examples

Create an ingest batch with a manual transcript:

```bash
curl -X POST http://localhost:8000/api/ingest/ \
  -H "Content-Type: application/json" \
  -d '{
    "input": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "manual_transcript": "The truth is consistency wins. The mistake is waiting for perfection."
  }'
```

Search:

```bash
curl -X POST http://localhost:8000/api/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "consistency",
    "search_type": "hybrid",
    "limit": 20,
    "filters": {}
  }'
```

Generate viral moments:

```bash
curl -X POST http://localhost:8000/api/videos/VIDEO_UUID/viral-moments/
```

## Project Layout

```text
backend/
  config/
  apps/videos/
    models.py
    tasks.py
    views.py
    services/
frontend/
  src/
    api/
    components/
    pages/
docker-compose.yml
Makefile
.env.example
```

## Troubleshooting

If the app cannot connect to Postgres, make sure `make dev` is running and migrations have been applied:

```bash
make migrate
```

If ingest fails with `No transcript provider could handle this video`, use the manual transcript box or enable a permitted provider in `.env`.

If playlist ingest fails, set `YOUTUBE_API_KEY`.

If frontend calls fail, confirm the backend is available at http://localhost:8000/api and `FRONTEND_ORIGIN=http://localhost:5173` is set in `.env`.

## Known Limitations

- Authorized YouTube captions and ASR providers are extension points, not complete adapters.
- Local fallback summaries are simple extractive summaries.
- The vector field is fixed at 1536 dimensions for `text-embedding-3-small`.
- Viral moments are timestamp suggestions only; this MVP does not create video clips.
