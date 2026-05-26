from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from django.conf import settings

from .base import TranscriptFetchResult, TranscriptProvider


class YtDlpSubtitleProvider(TranscriptProvider):
    def can_handle(self, video, context: dict) -> bool:
        return bool(settings.ENABLE_YTDLP_PROVIDER and context.get("allow_ytdlp", True))

    def fetch(self, video, context: dict) -> TranscriptFetchResult:
        with tempfile.TemporaryDirectory(prefix="videorecall-ytdlp-") as tmp:
            subtitle_result = self._fetch_subtitles(video, Path(tmp))
            if subtitle_result:
                return subtitle_result
            if self._can_download_audio_for_asr(context):
                return self._download_audio_and_transcribe(video, Path(tmp))
            raise RuntimeError(
                "No subtitles were available. Audio download/transcription fallback requires ENABLE_ASR_PROVIDER=true, "
                "ALLOW_MEDIA_DOWNLOADS_FOR_OWNED_CONTENT=true, OPENAI_API_KEY, and owned_content=true for this ingest."
            )

    def _fetch_subtitles(self, video, tmp: Path) -> TranscriptFetchResult | None:
        manual = self._run_subtitle_command(video, tmp, "--write-subs")
        manual_file = self._find_subtitle_file(tmp)
        if manual.returncode == 0 and manual_file:
            return self._subtitle_fetch_result(manual_file, "yt_dlp_manual_subtitle", auto=False)

        auto = self._run_subtitle_command(video, tmp, "--write-auto-subs")
        auto_file = self._find_subtitle_file(tmp)
        if auto.returncode == 0 and auto_file:
            return self._subtitle_fetch_result(auto_file, "yt_dlp_auto_subtitle", auto=True)
        return None

    def _run_subtitle_command(self, video, tmp: Path, mode: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                "yt-dlp",
                "--skip-download",
                mode,
                "--sub-langs",
                "en.*",
                "--sub-format",
                "vtt/srt",
                "-o",
                str(tmp / "%(id)s.%(ext)s"),
                video.canonical_url,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def _find_subtitle_file(self, tmp: Path) -> Path | None:
        files = sorted(tmp.glob("*.vtt")) or sorted(tmp.glob("*.srt"))
        return files[0] if files else None

    def _subtitle_fetch_result(self, path: Path, source_type: str, auto: bool) -> TranscriptFetchResult:
        raw_format = "vtt" if path.suffix == ".vtt" else "srt"
        return TranscriptFetchResult(
            source_type=source_type,
            language_code="en",
            raw_format=raw_format,
            raw_text=path.read_text(encoding="utf-8", errors="ignore"),
            metadata={"provider": "yt-dlp", "subtitle_only": True, "auto_subtitle": auto},
        )

    def _can_download_audio_for_asr(self, context: dict) -> bool:
        return bool(
            settings.ENABLE_ASR_PROVIDER
            and settings.ALLOW_MEDIA_DOWNLOADS_FOR_OWNED_CONTENT
            and settings.OPENAI_API_KEY
            and context.get("owned_content")
        )

    def _download_audio_and_transcribe(self, video, tmp: Path) -> TranscriptFetchResult:
        result = subprocess.run(
            [
                "yt-dlp",
                "-x",
                "--audio-format",
                "mp3",
                "--audio-quality",
                "5",
                "-o",
                str(tmp / "%(id)s.%(ext)s"),
                video.canonical_url,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "yt-dlp audio extraction failed")

        audio_files = sorted(tmp.glob("*.mp3")) or sorted(tmp.glob("*.m4a")) or sorted(tmp.glob("*.webm"))
        if not audio_files:
            raise RuntimeError("yt-dlp did not produce an audio file for ASR.")

        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        request_kwargs = _transcription_request_kwargs(settings.OPENAI_TRANSCRIPTION_MODEL)
        with audio_files[0].open("rb") as audio:
            transcription = client.audio.transcriptions.create(
                model=settings.OPENAI_TRANSCRIPTION_MODEL,
                file=audio,
                **request_kwargs,
            )
        payload = transcription.model_dump() if hasattr(transcription, "model_dump") else dict(transcription)
        raw_text = _segments_to_vtt(payload.get("segments", [])) or payload.get("text", "")
        raw_format = "vtt" if payload.get("segments") else "plain_text"
        return TranscriptFetchResult(
            source_type="asr_openai",
            language_code=payload.get("language", "en") or "en",
            raw_format=raw_format,
            raw_text=raw_text,
            metadata={"provider": "yt-dlp+openai-asr", "downloaded_audio_only": True, "raw": payload},
        )


def _transcription_request_kwargs(model: str) -> dict:
    if model.startswith("gpt-4o"):
        return {"response_format": "json"}
    return {"response_format": "verbose_json", "timestamp_granularities": ["segment"]}


def _segments_to_vtt(segments: list[dict]) -> str:
    if not segments:
        return ""
    lines = ["WEBVTT", ""]
    for segment in segments:
        start = _seconds_to_vtt_time(float(segment.get("start", 0)))
        end = _seconds_to_vtt_time(float(segment.get("end", segment.get("start", 0))))
        text = str(segment.get("text", "")).strip()
        if text:
            lines.extend([f"{start} --> {end}", text, ""])
    return "\n".join(lines)


def _seconds_to_vtt_time(value: float) -> str:
    millis = int(round(value * 1000))
    hours, remainder = divmod(millis, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{millis:03}"
