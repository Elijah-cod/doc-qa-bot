"""Offline stand-ins for Gemini and Supabase, used by route tests."""
import hashlib
import math
import re

from app.store import RetrievedChunk

DIM = 64


class FakeEmbedder:
    """Bag-of-words hashing: texts sharing words get similar vectors. Deterministic, free, instant."""

    def __init__(self, fail_with: Exception | None = None):
        self.calls: list[tuple[str, int]] = []  # (task, number of texts)
        self.fail_with = fail_with

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * DIM
        for word in re.findall(r"\w+", text.lower()):
            v[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def embed_documents(self, texts):
        self.calls.append(("document", len(texts)))
        if self.fail_with:
            raise self.fail_with
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        self.calls.append(("query", 1))
        if self.fail_with:
            raise self.fail_with
        return self._vec(text)


class InMemoryStore:
    """Same interface as SupabaseStore, backed by a list. Can be told to fail on insert."""

    def __init__(self, fail_insert_with: Exception | None = None):
        self.rows: list[dict] = []
        self.fail_insert_with = fail_insert_with
        self.deleted: list[str] = []

    def insert_chunks(self, doc_id, chunks, vectors):
        # Simulate a partial write: first row lands, then the failure.
        for i, (c, v) in enumerate(zip(chunks, vectors)):
            if self.fail_insert_with and i == 1:
                raise self.fail_insert_with
            self.rows.append({"id": len(self.rows) + 1, "doc_id": doc_id, "page": c.page,
                              "chunk_index": c.chunk_index, "content": c.content, "embedding": v})

    def match(self, doc_id, query_vector, k):
        scored = [
            RetrievedChunk(id=r["id"], page=r["page"], chunk_index=r["chunk_index"], content=r["content"],
                           score=sum(a * b for a, b in zip(r["embedding"], query_vector)))
            for r in self.rows if r["doc_id"] == doc_id
        ]
        return sorted(scored, key=lambda c: c.score, reverse=True)[:k]

    def delete_document(self, doc_id):
        before = len(self.rows)
        self.rows = [r for r in self.rows if r["doc_id"] != doc_id]
        self.deleted.append(doc_id)
        return before - len(self.rows)

    def doc_rows(self, doc_id):
        return [r for r in self.rows if r["doc_id"] == doc_id]
