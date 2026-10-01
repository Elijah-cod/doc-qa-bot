"""Vector storage. The routes depend on the VectorStore *shape*, so tests can use an
in-memory fake while the real app uses Supabase."""
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from app.chunking import Chunk
from app.db import get_supabase, to_pgvector


class StoreError(RuntimeError):
    """The database call failed (network, permissions, bad data)."""


@dataclass(frozen=True)
class RetrievedChunk:
    id: int
    page: int
    chunk_index: int
    content: str
    score: float  # cosine similarity, higher = more relevant


class VectorStore(Protocol):
    def insert_chunks(self, doc_id: str, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...
    def match(self, doc_id: str, query_vector: list[float], k: int) -> list[RetrievedChunk]: ...
    def delete_document(self, doc_id: str) -> int: ...


class SupabaseStore:
    def __init__(self, client, batch_size: int = 100):
        self.client = client
        self.batch_size = batch_size  # rows per insert request; keeps each HTTP body small

    def insert_chunks(self, doc_id, chunks, vectors):
        if len(chunks) != len(vectors):
            raise StoreError(f"{len(chunks)} chunks but {len(vectors)} vectors")
        rows = [
            {"doc_id": doc_id, "page": c.page, "chunk_index": c.chunk_index,
             "content": c.content, "embedding": to_pgvector(v)}
            for c, v in zip(chunks, vectors)
        ]
        try:
            for start in range(0, len(rows), self.batch_size):
                self.client.table("chunks").insert(rows[start : start + self.batch_size]).execute()
        except Exception as e:
            raise StoreError(f"Insert failed: {e}") from e

    def match(self, doc_id, query_vector, k):
        try:
            res = self.client.rpc(
                "match_chunks",
                {"query_embedding": to_pgvector(query_vector), "p_doc_id": doc_id, "match_count": k},
            ).execute()
        except Exception as e:
            raise StoreError(f"Search failed: {e}") from e
        return [RetrievedChunk(**row) for row in res.data]

    def delete_document(self, doc_id):
        try:
            res = self.client.table("chunks").delete().eq("doc_id", doc_id).execute()
        except Exception as e:
            raise StoreError(f"Delete failed: {e}") from e
        return len(res.data or [])


@lru_cache
def get_store() -> SupabaseStore:
    return SupabaseStore(get_supabase())
