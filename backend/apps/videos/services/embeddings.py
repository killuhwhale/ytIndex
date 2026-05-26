from __future__ import annotations

import hashlib

from django.conf import settings


def deterministic_embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    for i in range(settings.EMBEDDING_DIMENSIONS):
        byte = digest[i % len(digest)]
        values.append((byte / 127.5) - 1.0)
    return values


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not settings.OPENAI_API_KEY:
        return [deterministic_embedding(text) for text in texts]
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.embeddings.create(model=settings.EMBEDDING_MODEL, input=texts)
    except Exception:
        return [deterministic_embedding(text) for text in texts]
    return [item.embedding for item in response.data]
