from __future__ import annotations

import json
from dataclasses import dataclass
import re

from django.conf import settings


SUMMARY_KEYS = {
    "short_summary": "",
    "detailed_summary": "",
    "key_points": [],
    "topics": [],
    "important_quotes": [],
    "action_items": [],
    "controversies": [],
    "glossary": [],
}


@dataclass(frozen=True)
class SummaryChunk:
    index: int
    start_ms: int
    end_ms: int
    text: str


def summarize_transcript(video, chunks) -> dict:
    summary_chunks = [
        SummaryChunk(index=chunk.chunk_index, start_ms=chunk.start_ms, end_ms=chunk.end_ms, text=chunk.text)
        for chunk in chunks
        if chunk.text.strip()
    ]
    text = "\n\n".join(_format_chunk(chunk) for chunk in summary_chunks)
    if not settings.OPENAI_API_KEY:
        return _fallback_summary(text)

    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        if len(summary_chunks) > 10:
            chunk_summaries = [_summarize_chunk_group(client, video, group) for group in _groups(summary_chunks, 8)]
            data = _final_summary(client, video, "\n\n".join(chunk_summaries), source_is_notes=True)
        else:
            data = _final_summary(client, video, text, source_is_notes=False)
    except Exception:
        return _fallback_summary(text)

    data = _normalize_summary(data)
    data["generated_by"] = settings.OPENAI_SUMMARY_MODEL
    return data


def _summarize_chunk_group(client, video, chunks: list[SummaryChunk]) -> str:
    prompt = (
        "You are preparing factual notes for a video summary. Use only the transcript excerpts. "
        "Preserve timestamps in seconds as [start_s-end_s]. Capture claims, examples, steps, quotes, disagreements, and action items. "
        "Do not add information that is not present.\n\n"
        f"Video title: {video.title}\n\n"
        f"Transcript excerpts:\n{chr(10).join(_format_chunk(chunk) for chunk in chunks)}"
    )
    response = client.chat.completions.create(
        model=settings.OPENAI_SUMMARY_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


def _final_summary(client, video, source_text: str, source_is_notes: bool) -> dict:
    source_label = "section notes" if source_is_notes else "timestamped transcript excerpts"
    prompt = (
        "Return only valid compact JSON for a high-quality video intelligence summary.\n"
        "Use this exact schema:\n"
        "{\n"
        '  "short_summary": "3-5 sentence executive summary",\n'
        '  "detailed_summary": "clear multi-paragraph summary covering the full video in chronological order",\n'
        '  "key_points": ["specific point with useful detail"],\n'
        '  "topics": [{"name": "topic", "summary": "what was said", "start_ms": 0, "end_ms": 0}],\n'
        '  "important_quotes": [{"quote": "verbatim quote", "start_ms": 0, "end_ms": 0, "reason": "why it matters"}],\n'
        '  "action_items": [{"text": "recommended action", "start_ms": 0, "end_ms": 0}],\n'
        '  "controversies": [{"text": "debate or tension", "start_ms": 0, "end_ms": 0}],\n'
        '  "glossary": [{"term": "term", "definition": "definition from context"}]\n'
        "}\n\n"
        "Rules:\n"
        "- Cover the whole video, not just the opening.\n"
        "- Be concrete: include names, examples, numbers, tools, causes, conclusions, and caveats when present.\n"
        "- Preserve timestamps by converting [start_s-end_s] into start_ms/end_ms integers.\n"
        "- Do not invent quotes, topics, controversies, or actions. Use empty arrays when absent.\n"
        "- Avoid vague filler such as 'the speaker discusses various topics'.\n\n"
        f"Video title: {video.title}\n"
        f"Source {source_label}:\n{source_text[:42000]}"
    )
    response = client.chat.completions.create(
        model=settings.OPENAI_SUMMARY_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content or "{}")


def _format_chunk(chunk: SummaryChunk) -> str:
    return f"[{chunk.start_ms // 1000}-{chunk.end_ms // 1000}] {chunk.text}"


def _groups(items: list[SummaryChunk], size: int):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _normalize_summary(data: dict) -> dict:
    output = {key: data.get(key, default) for key, default in SUMMARY_KEYS.items()}
    output["short_summary"] = str(output["short_summary"] or "").strip()
    output["detailed_summary"] = str(output["detailed_summary"] or "").strip()
    if not output["detailed_summary"]:
        output["detailed_summary"] = output["short_summary"]
    for key in ["key_points", "topics", "important_quotes", "action_items", "controversies", "glossary"]:
        if not isinstance(output[key], list):
            output[key] = []
    return output


def _fallback_summary(text: str) -> dict:
    clean_text = _strip_summary_markers(text)
    sentences = _sentences(clean_text)
    selected = _representative_sentences(sentences, limit=8)
    short_sentences = selected[:3] or sentences[:3]
    short = " ".join(short_sentences).strip()
    detailed = "\n\n".join(_representative_sentences(sentences, limit=12)) or short
    key_points = [sentence[:260] for sentence in selected[:8]]
    return {
        "short_summary": short or "No transcript text was available to summarize.",
        "detailed_summary": detailed or short,
        "key_points": key_points,
        "topics": [],
        "important_quotes": [],
        "action_items": [],
        "controversies": [],
        "glossary": [],
        "generated_by": "local-fallback",
    }


def _strip_summary_markers(text: str) -> str:
    text = re.sub(r"\[\d+\s*-\s*\d+\]\s*", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _sentences(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return [part if part.endswith((".", "!", "?")) else f"{part}." for part in parts]


def _representative_sentences(sentences: list[str], limit: int) -> list[str]:
    if len(sentences) <= limit:
        return sentences
    stopwords = {
        "the", "and", "that", "this", "with", "you", "for", "but", "are", "was", "have", "not", "they",
        "from", "what", "when", "your", "about", "there", "would", "could", "just", "like", "into",
    }
    frequencies: dict[str, int] = {}
    for sentence in sentences:
        for word in re.findall(r"[a-zA-Z][a-zA-Z']+", sentence.lower()):
            if len(word) > 3 and word not in stopwords:
                frequencies[word] = frequencies.get(word, 0) + 1
    scored = []
    for index, sentence in enumerate(sentences):
        words = re.findall(r"[a-zA-Z][a-zA-Z']+", sentence.lower())
        score = sum(frequencies.get(word, 0) for word in words) / max(1, len(words))
        if 8 <= len(words) <= 45:
            score += 1.0
        scored.append((score, index, sentence))
    chosen = sorted(sorted(scored, reverse=True)[:limit], key=lambda item: item[1])
    return [sentence for _, _, sentence in chosen]
