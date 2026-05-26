from __future__ import annotations

from .base import TranscriptProvider


class YouTubeApiCaptionProvider(TranscriptProvider):
    """Placeholder for authorized YouTube captions access.

    The MVP deliberately does not implement OAuth caption downloads. This provider
    exists to keep the provider chain explicit and compliant.
    """

    def can_handle(self, video, context: dict) -> bool:
        return False

    def fetch(self, video, context: dict):
        raise RuntimeError("Authorized YouTube captions access is not configured.")
