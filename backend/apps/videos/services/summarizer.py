from __future__ import annotations

import json

from django.conf import settings


def summarize_transcript(video, chunks) -> dict:
    text = " ".join(chunk.text for chunk in chunks)[:12000]
    if not settings.OPENAI_API_KEY:
        return _fallback_summary(text)

    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    prompt = (
        "Return compact JSON with keys short_summary, detailed_summary, key_points, "
        "topics, important_quotes, action_items, controversies, glossary. Preserve timestamps if present.\n\n"
        f"Title: {video.title}\nTranscript:\n{text}"
    )
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_SUMMARY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
    except Exception:
        return _fallback_summary(text)

    data = json.loads(response.choices[0].message.content or "{}")
    data["generated_by"] = settings.OPENAI_SUMMARY_MODEL
    return data


def _fallback_summary(text: str) -> dict:
    sentences = [part.strip() for part in text.replace("\n", " ").split(".") if part.strip()]
    short = ". ".join(sentences[:4]) + ("." if sentences else "")
    key_points = [sentence[:240] for sentence in sentences[:6]]
    return {
        "short_summary": short or "No transcript text was available to summarize.",
        "detailed_summary": short,
        "key_points": key_points,
        "topics": [],
        "important_quotes": [],
        "action_items": [],
        "controversies": [],
        "glossary": [],
        "generated_by": "local-fallback",
    }
