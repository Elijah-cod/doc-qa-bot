from uuid import UUID

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.embeddings import Embedder, EmbeddingError, get_embedder
from app.generation import GenerationError, Generator, get_generator
from app.ingest import ingest_pdf
from app.parsing import PDFParseError
from app.rag import DocumentNotFound, answer_question
from app.store import StoreError, VectorStore, get_store

app = FastAPI(title="Doc Q&A Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().origins,  # only our frontend may call the API from a browser
    allow_methods=["*"],
    allow_headers=["*"],
)


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    pages: int
    chunks: int


class DeleteResponse(BaseModel):
    doc_id: str
    deleted_chunks: int


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/upload", response_model=UploadResponse)
def upload(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    embedder: Embedder = Depends(get_embedder),
    store: VectorStore = Depends(get_store),
):
    # 1. Cheap checks first: is this even claiming to be a PDF?
    name = file.filename or "upload.pdf"
    if not (name.lower().endswith(".pdf") or file.content_type == "application/pdf"):
        raise HTTPException(415, "Only PDF files are supported.")

    # 2. Size cap: read at most limit+1 bytes so a huge file can't eat memory.
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB.")

    # 3. Real PDFs start with the magic bytes %PDF- (don't trust the file name).
    if b"%PDF-" not in data[:1024]:
        raise HTTPException(415, "File is not a PDF.")

    # 4. The pipeline. Each failure type maps to a status code the UI can explain.
    try:
        result = ingest_pdf(data, embedder=embedder, store=store, settings=settings)
    except PDFParseError as e:
        raise HTTPException(422, str(e))
    except EmbeddingError as e:
        raise HTTPException(502, f"Embedding service failed: {e}")
    except StoreError as e:
        raise HTTPException(503, f"Database unavailable: {e}")

    return UploadResponse(doc_id=result.doc_id, filename=name, pages=result.pages, chunks=result.chunks)


@app.delete("/documents/{doc_id}", response_model=DeleteResponse)
@app.post("/documents/{doc_id}/delete", response_model=DeleteResponse, include_in_schema=False)
def delete_document(doc_id: str, store: VectorStore = Depends(get_store)):
    # The POST alias exists for navigator.sendBeacon(), which browsers use to fire a
    # request while the tab is closing. sendBeacon can only POST.
    try:
        n = store.delete_document(doc_id)
    except StoreError as e:
        raise HTTPException(503, f"Database unavailable: {e}")
    if n == 0:
        raise HTTPException(404, "Document not found.")
    return DeleteResponse(doc_id=doc_id, deleted_chunks=n)


class AskRequest(BaseModel):
    doc_id: UUID  # FastAPI rejects anything that isn't a valid UUID with a 422
    question: str = Field(min_length=1, max_length=1000)


class SourceOut(BaseModel):
    n: int
    page: int
    chunk_index: int
    score: float
    content: str
    cited: bool


class AskResponse(BaseModel):
    answer: str
    grounded: bool
    sources: list[SourceOut]


@app.post("/ask", response_model=AskResponse)
def ask(
    req: AskRequest,
    settings: Settings = Depends(get_settings),
    embedder: Embedder = Depends(get_embedder),
    store: VectorStore = Depends(get_store),
    generator: Generator = Depends(get_generator),
):
    if not req.question.strip():
        raise HTTPException(422, "Question is empty.")
    try:
        result = answer_question(req.question, str(req.doc_id), embedder=embedder, store=store,
                                 generator=generator, settings=settings)
    except DocumentNotFound:
        raise HTTPException(404, "Document not found. Upload it again.")
    except (EmbeddingError, GenerationError) as e:
        raise HTTPException(502, f"AI service failed: {e}")
    except StoreError as e:
        raise HTTPException(503, f"Database unavailable: {e}")

    return AskResponse(
        answer=result.answer,
        grounded=result.grounded,
        sources=[SourceOut(n=s.n, page=s.chunk.page, chunk_index=s.chunk.chunk_index,
                           score=round(s.chunk.score, 4), content=s.chunk.content, cited=s.cited)
                 for s in result.sources],
    )
