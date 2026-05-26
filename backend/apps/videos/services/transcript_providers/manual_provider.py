from __future__ import annotations

from .base import TranscriptFetchResult, TranscriptProvider


class ManualTranscriptProvider(TranscriptProvider):
    def can_handle(self, video, context: dict) -> bool:
        return bool(context.get("manual_transcript"))

    def fetch(self, video, context: dict) -> TranscriptFetchResult:
        return TranscriptFetchResult(
            source_type="manual_upload",
            language_code=context.get("language_code", "en"),
            raw_format=context.get("raw_format", "plain_text"),
            raw_text=context["manual_transcript"],
            metadata={"provided_by": "user"},
        )
