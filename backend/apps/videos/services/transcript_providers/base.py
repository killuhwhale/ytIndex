from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TranscriptFetchResult:
    source_type: str
    language_code: str
    raw_format: str
    raw_text: str
    segments: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class TranscriptProvider:
    def can_handle(self, video, context: dict) -> bool:
        raise NotImplementedError

    def fetch(self, video, context: dict) -> TranscriptFetchResult:
        raise NotImplementedError
