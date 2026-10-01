"""Step 4: the ingestion pipeline, PDF bytes -> parse -> chunk -> embed -> store."""
import uuid
from dataclasses import dataclass

from app.chunking import chunk_pages
from app.config import Settings
from app.embeddings import Embedder
from app.parsing import parse_pdf
from app.store import VectorStore


@dataclass(frozen=True)
class IngestResult:
    doc_id: str
    pages: int
    chunks: int


def ingest_pdf(data: bytes, *, embedder: Embedder, store: VectorStore, settings: Settings) -> IngestResult:
    pages = parse_pdf(data, max_pages=settings.max_pages)                  # may raise PDFParseError
    chunks = chunk_pages(pages, settings.chunk_tokens, settings.chunk_overlap_tokens)
    vectors = embedder.embed_documents([c.content for c in chunks])         # may raise EmbeddingError

    # Embed everything BEFORE writing anything: if Gemini fails, the DB is untouched.
    doc_id = str(uuid.uuid4())
    try:
        store.insert_chunks(doc_id, chunks, vectors)
    except Exception:
        # A batch may have landed before the failure; don't leave half a document behind.
        try:
            store.delete_document(doc_id)
        except Exception:
            pass
        raise
    return IngestResult(doc_id=doc_id, pages=len(pages), chunks=len(chunks))
