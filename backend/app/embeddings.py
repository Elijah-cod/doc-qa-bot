"""Step 3: text -> vectors with Gemini.

Two task types, because Gemini embeds questions and passages slightly differently
so that a question lands close to the passage that *answers* it:
  - RETRIEVAL_DOCUMENT for chunks we store
  - RETRIEVAL_QUERY    for the user's question
"""
import math
import time
from collections.abc import Callable
from functools import lru_cache
from typing import Protocol

from google import genai
from google.genai import errors, types

from app.config import get_settings

# 429 = rate limit / quota, 5xx = Google-side hiccup. Both are worth retrying.
RETRYABLE_CODES = {429, 500, 502, 503, 504}


class EmbeddingError(RuntimeError):
    """Embedding failed for good (bad key, bad input, or retries exhausted)."""


class Embedder(Protocol):
    """Anything with these two methods can be used as an embedder (real or fake)."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


def normalize(vec: list[float]) -> list[float]:
    """Scale to length 1. Gemini only pre-normalizes full-size (3072) vectors."""
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm else vec


class GeminiEmbedder:
    def __init__(
        self,
        client: genai.Client,
        model: str,
        dim: int,
        batch_size: int = 100,
        max_retries: int = 5,
        base_delay: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,  # injectable so tests don't really wait
    ):
        self.client = client
        self.model = model
        self.dim = dim
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.sleep = sleep

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            response = self._call_with_retry(batch, task_type)
            embeddings = response.embeddings or []
            if len(embeddings) != len(batch):
                raise EmbeddingError(f"Asked for {len(batch)} embeddings, got {len(embeddings)}.")
            for e in embeddings:
                if len(e.values) != self.dim:
                    raise EmbeddingError(f"Expected {self.dim} dims, got {len(e.values)}. Check EMBED_DIM.")
                vectors.append(normalize(e.values))
        return vectors

    def _call_with_retry(self, batch: list[str], task_type: str):
        config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=self.dim)
        for attempt in range(self.max_retries + 1):
            try:
                return self.client.models.embed_content(model=self.model, contents=batch, config=config)
            except errors.APIError as e:
                if e.code not in RETRYABLE_CODES:
                    raise EmbeddingError(f"Gemini rejected the request ({e.code} {e.status}).") from e
                if attempt == self.max_retries:
                    raise EmbeddingError(f"Gemini still failing after {self.max_retries} retries ({e.code}).") from e
                # Exponential backoff: 1s, 2s, 4s, 8s, ... capped at 30s.
                self.sleep(min(self.base_delay * 2**attempt, 30.0))
        raise AssertionError("unreachable")


@lru_cache
def get_embedder() -> GeminiEmbedder:
    s = get_settings()
    if not s.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY missing from .env")
    return GeminiEmbedder(
        client=genai.Client(api_key=s.gemini_api_key),
        model=s.embed_model,
        dim=s.embed_dim,
        batch_size=s.embed_batch_size,
    )
