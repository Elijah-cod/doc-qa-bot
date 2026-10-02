"""Production hardening: rate limits, readiness, CORS regex."""
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.embeddings import get_embedder
from app.generation import get_generator
from app.main import app
from app.ratelimit import SlidingWindow
from app.store import StoreError, get_store
from tests.fakes import FakeEmbedder, FakeGenerator, InMemoryStore


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_sliding_window_blocks_then_recovers():
    clock = FakeClock()
    w = SlidingWindow(clock)
    assert w.hit("ip", limit=2, window=60) is None
    assert w.hit("ip", limit=2, window=60) is None
    assert w.hit("ip", limit=2, window=60) == pytest.approx(60)   # blocked, full window to wait
    clock.t += 30
    assert w.hit("ip", limit=2, window=60) == pytest.approx(30)   # still blocked, half left
    clock.t += 31
    assert w.hit("ip", limit=2, window=60) is None                 # oldest hit expired


def test_sliding_window_is_per_key():
    w = SlidingWindow(FakeClock())
    assert w.hit("a", limit=1) is None
    assert w.hit("b", limit=1) is None
    assert w.hit("a", limit=1) is not None


@pytest.fixture
def client():
    state = {"settings": Settings(_env_file=None, upload_limit_per_hour=2, ask_limit_per_hour=1, score_cutoff=0.0)}
    store = InMemoryStore()
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_generator] = lambda: FakeGenerator()
    app.dependency_overrides[get_settings] = lambda: state["settings"]
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_upload_rate_limit_returns_429_with_retry_after(client, make_pdf):
    pdf = make_pdf(["hello"])
    for _ in range(2):
        assert client.post("/upload", files={"file": ("a.pdf", pdf, "application/pdf")}).status_code == 200
    r = client.post("/upload", files={"file": ("a.pdf", pdf, "application/pdf")})
    assert r.status_code == 429
    assert "Too many upload requests" in r.json()["detail"]
    assert int(r.headers["Retry-After"]) > 0


def test_ask_rate_limit(client, make_pdf):
    doc_id = client.post("/upload", files={"file": ("a.pdf", make_pdf(["hello world"]), "application/pdf")}).json()["doc_id"]
    assert client.post("/ask", json={"doc_id": doc_id, "question": "hello"}).status_code == 200
    assert client.post("/ask", json={"doc_id": doc_id, "question": "hello"}).status_code == 429


def test_zero_disables_limit(client, make_pdf):
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, upload_limit_per_hour=0)
    pdf = make_pdf(["x"])
    codes = {client.post("/upload", files={"file": ("a.pdf", pdf, "application/pdf")}).status_code for _ in range(5)}
    assert codes == {200}


def test_ready_ok_and_failing(client):
    assert client.get("/ready").json() == {"ok": True, "database": "ok"}
    app.dependency_overrides[get_store] = lambda: InMemoryStore(fail_insert_with=StoreError("down"))
    assert client.get("/ready").status_code == 503


def test_health_needs_no_dependencies():
    assert TestClient(app).get("/health").json() == {"ok": True}
