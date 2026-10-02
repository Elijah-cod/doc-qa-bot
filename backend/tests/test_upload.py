"""/upload and DELETE /documents route tests, fully offline (fake embedder + in-memory store)."""
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.embeddings import EmbeddingError, get_embedder
from app.main import app
from app.store import StoreError, get_store
from tests.fakes import FakeEmbedder, InMemoryStore


@pytest.fixture
def deps():
    """Swap the real Gemini/Supabase/.env dependencies for fakes; undo after each test."""
    state = {"embedder": FakeEmbedder(), "store": InMemoryStore(),
             "settings": Settings(_env_file=None, max_pages=5, max_upload_mb=1)}
    app.dependency_overrides[get_embedder] = lambda: state["embedder"]
    app.dependency_overrides[get_store] = lambda: state["store"]
    app.dependency_overrides[get_settings] = lambda: state["settings"]
    yield state
    app.dependency_overrides.clear()


@pytest.fixture
def client(deps):
    return TestClient(app)


def upload(client, data: bytes, name="doc.pdf", ctype="application/pdf"):
    return client.post("/upload", files={"file": (name, data, ctype)})


def test_valid_pdf_is_ingested(client, deps, make_pdf):
    r = upload(client, make_pdf(["Cats are great pets.", "", "The codename is BLUEHERON."]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["filename"] == "doc.pdf"
    assert body["pages"] == 3 and body["chunks"] == 2

    rows = deps["store"].doc_rows(body["doc_id"])
    assert [r["page"] for r in rows] == [1, 3]
    assert "BLUEHERON" in rows[1]["content"]
    assert deps["embedder"].calls == [("document", 2)]  # one batched call, document task type


def test_each_upload_gets_its_own_doc_id(client, make_pdf):
    a = upload(client, make_pdf(["one"])).json()["doc_id"]
    b = upload(client, make_pdf(["two"])).json()["doc_id"]
    assert a != b


def test_non_pdf_extension_rejected(client):
    r = upload(client, b"hello", name="notes.txt", ctype="text/plain")
    assert r.status_code == 415


def test_renamed_text_file_rejected_by_magic_bytes(client):
    r = upload(client, b"just text pretending", name="fake.pdf")
    assert r.status_code == 415
    assert "not a PDF" in r.json()["detail"]


def test_oversized_file_rejected(client):
    r = upload(client, b"%PDF-" + b"0" * (1024 * 1024))  # just over the 1 MB test limit
    assert r.status_code == 413


def test_pdf_without_text_returns_422(client, deps, make_pdf):
    r = upload(client, make_pdf(["", ""]))
    assert r.status_code == 422
    assert "scanned" in r.json()["detail"]
    assert deps["embedder"].calls == []  # never paid for embeddings


def test_too_many_pages_returns_422(client, make_pdf):
    r = upload(client, make_pdf(["p"] * 6))  # limit is 5 in this test
    assert r.status_code == 422
    assert "limit is 5" in r.json()["detail"]


def test_embedding_failure_returns_502_and_stores_nothing(client, deps, make_pdf):
    deps["embedder"] = FakeEmbedder(fail_with=EmbeddingError("quota"))
    r = upload(client, make_pdf(["text"]))
    assert r.status_code == 502
    assert deps["store"].rows == []


def test_store_failure_returns_503_and_cleans_up(client, deps, make_pdf):
    deps["store"] = InMemoryStore(fail_insert_with=StoreError("db down"))
    r = upload(client, make_pdf(["page one text", "page two text"]))
    assert r.status_code == 503
    assert deps["store"].rows == []            # the partial first row was removed
    assert len(deps["store"].deleted) == 1     # cleanup ran


def test_delete_document(client, make_pdf):
    doc_id = upload(client, make_pdf(["a", "b"])).json()["doc_id"]
    r = client.delete(f"/documents/{doc_id}")
    assert r.status_code == 200 and r.json()["deleted_chunks"] == 2
    assert client.delete(f"/documents/{doc_id}").status_code == 404


def test_cors_allows_frontend_origin(client):
    r = client.options("/upload", headers={"Origin": "http://localhost:3000",
                                           "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_beacon_delete_alias(client, make_pdf):
    doc_id = upload(client, make_pdf(["a"])).json()["doc_id"]
    r = client.post(f"/documents/{doc_id}/delete")   # what navigator.sendBeacon sends
    assert r.status_code == 200 and r.json()["deleted_chunks"] == 1
