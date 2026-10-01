"""/ask route tests, offline: fake embedder + in-memory store + fake LLM."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.embeddings import get_embedder
from app.generation import GenerationError, get_generator
from app.main import app
from app.rag import NOT_FOUND
from app.store import get_store
from tests.fakes import FakeEmbedder, FakeGenerator, InMemoryStore


@pytest.fixture
def deps():
    state = {"embedder": FakeEmbedder(), "store": InMemoryStore(), "generator": FakeGenerator(),
             "settings": Settings(_env_file=None, score_cutoff=0.3)}
    app.dependency_overrides[get_embedder] = lambda: state["embedder"]
    app.dependency_overrides[get_store] = lambda: state["store"]
    app.dependency_overrides[get_generator] = lambda: state["generator"]
    app.dependency_overrides[get_settings] = lambda: state["settings"]
    yield state
    app.dependency_overrides.clear()


@pytest.fixture
def client(deps):
    return TestClient(app)


@pytest.fixture
def doc_id(client, make_pdf):
    pdf = make_pdf(["Cats are small furry pets that purr.", "The project codename is BLUEHERON."])
    return client.post("/upload", files={"file": ("d.pdf", pdf, "application/pdf")}).json()["doc_id"]


def test_answer_with_sources(client, deps, doc_id):
    r = client.post("/ask", json={"doc_id": doc_id, "question": "What is the project codename?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["grounded"] is True
    assert body["answer"] == "The codename is BLUEHERON [1]."
    top = body["sources"][0]
    assert top["n"] == 1 and top["page"] == 2 and "BLUEHERON" in top["content"] and top["cited"] is True
    scores = [s["score"] for s in body["sources"]]
    assert scores == sorted(scores, reverse=True)


def test_off_topic_question_is_gated(client, deps, doc_id):
    r = client.post("/ask", json={"doc_id": doc_id, "question": "Explain quantum chromodynamics"})
    body = r.json()
    assert body["grounded"] is False and body["answer"] == NOT_FOUND
    assert deps["generator"].prompts == []


def test_unknown_doc_is_404(client):
    r = client.post("/ask", json={"doc_id": str(uuid.uuid4()), "question": "hi"})
    assert r.status_code == 404


@pytest.mark.parametrize("payload", [
    {"doc_id": "not-a-uuid", "question": "hi"},
    {"doc_id": str(uuid.uuid4()), "question": ""},
    {"doc_id": str(uuid.uuid4()), "question": "   "},
    {"doc_id": str(uuid.uuid4()), "question": "x" * 1001},
    {"question": "missing doc id"},
])
def test_bad_requests_are_422(client, payload):
    assert client.post("/ask", json=payload).status_code == 422


def test_llm_failure_is_502(client, deps, doc_id):
    deps["generator"] = FakeGenerator(fail_with=GenerationError("blocked"))
    r = client.post("/ask", json={"doc_id": doc_id, "question": "What is the project codename?"})
    assert r.status_code == 502
