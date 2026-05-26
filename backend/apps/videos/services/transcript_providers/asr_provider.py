from __future__ import annotations

from django.conf import settings

from .base import TranscriptProvider


class AsrProvider(TranscriptProvider):
    def can_handle(self, video, context: dict) -> bool:
        return bool(settings.ENABLE_ASR_PROVIDER and settings.ALLOW_MEDIA_DOWNLOADS_FOR_OWNED_CONTENT and context.get("owned_content"))

    def fetch(self, video, context: dict):
        raise RuntimeError("ASR fallback is configured as an extension point; audio extraction is not enabled in the MVP.")
