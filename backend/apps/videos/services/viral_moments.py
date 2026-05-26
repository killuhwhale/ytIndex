from __future__ import annotations

import re


HOOK_PATTERNS = [
    "most people",
    "the mistake",
    "the truth",
    "i learned",
    "nobody",
    "everyone thinks",
    "what changed",
    "the problem",
    "you should",
    "surprising",
]


def generate_viral_candidates(video, segments, limit: int = 8) -> list[dict]:
    windows = _windows(segments)
    scored = sorted((_score_window(window) for window in windows), key=lambda item: item["score"], reverse=True)
    return [
        {
            "start_ms": item["start_ms"],
            "end_ms": item["end_ms"],
            "hook": item["hook"],
            "quote": item["quote"],
            "reason": item["reason"],
            "score": round(item["score"], 3),
            "suggested_title": item["hook"][:90],
            "suggested_caption": item["quote"][:220],
            "tags": item["tags"],
        }
        for item in scored[:limit]
        if item["score"] > 0.2
    ]


def _windows(segments):
    window = []
    start = None
    for segment in segments:
        start = segment.start_ms if start is None else start
        window.append(segment)
        if segment.end_ms - start >= 60000:
            yield window
            window = []
            start = None
    if window:
        yield window


def _score_window(window) -> dict:
    text = " ".join(item.text for item in window)
    lower = text.lower()
    hook_hits = sum(1 for pattern in HOOK_PATTERNS if pattern in lower)
    punctuation = lower.count("!") + lower.count("?")
    concise = 1 if 18 <= len(text.split()) <= 180 else 0
    number_bonus = 1 if re.search(r"\b\d+[%x]?\b", lower) else 0
    score = min(1.0, 0.18 * hook_hits + 0.08 * punctuation + 0.12 * concise + 0.08 * number_bonus)
    hook = next((sentence.strip() for sentence in re.split(r"[.!?]", text) if sentence.strip()), text[:120])
    return {
        "start_ms": window[0].start_ms,
        "end_ms": window[-1].end_ms,
        "hook": hook[:180],
        "quote": text[:500],
        "reason": "Transcript window has hook phrases, concise context, or strong teaching/contrast language.",
        "score": score,
        "tags": ["clip-idea", "transcript"],
    }
