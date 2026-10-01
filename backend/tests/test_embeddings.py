"""Embedder unit tests. The Gemini client is replaced by a fake, so no network."""
import math
from types import SimpleNamespace

import pytest
from google.genai import errors

from app.embeddings import EmbeddingError, GeminiEmbedder, normalize

DIM = 8


class FakeModels:
    """Stands in for client.models. Records calls; can fail the first N calls."""

    def __init__(self, failures=(), dim=DIM, drop_one=False):
        self.calls = []
        self.failures = list(failures)  # exceptions to raise, in order, before succeeding
        self.dim = dim
        self.drop_one = drop_one

    def embed_content(self, *, model, contents, config):
        self.calls.append(SimpleNamespace(model=model, contents=list(contents), config=config))
        if self.failures:
            raise self.failures.pop(0)
        n = len(contents) - (1 if self.drop_one else 0)
        # vector i = [i+1, 0, 0, ...] so we can check order and normalization
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[float(i + 1)] + [0.0] * (self.dim - 1)) for i in range(n)])


def make_embedder(models, **kw):
    sleeps = []
    emb = GeminiEmbedder(SimpleNamespace(models=models), model="test-model", dim=DIM,
                         sleep=sleeps.append, **kw)
    return emb, sleeps


def api_error(code):
    cls = errors.ClientError if code < 500 else errors.ServerError
    return cls(code, {"error": {"code": code, "message": "boom", "status": "X"}})


def test_batches_and_keeps_order():
    models = FakeModels()
    emb, _ = make_embedder(models, batch_size=100)
    vecs = emb.embed_documents([f"t{i}" for i in range(250)])
    assert [len(c.contents) for c in models.calls] == [100, 100, 50]
    assert models.calls[2].contents[0] == "t200"
    assert len(vecs) == 250


def test_document_vs_query_task_types_and_dim():
    models = FakeModels()
    emb, _ = make_embedder(models)
    emb.embed_documents(["a chunk"])
    emb.embed_query("a question")
    assert models.calls[0].config.task_type == "RETRIEVAL_DOCUMENT"
    assert models.calls[1].config.task_type == "RETRIEVAL_QUERY"
    assert all(c.config.output_dimensionality == DIM for c in models.calls)
    assert all(c.model == "test-model" for c in models.calls)


def test_vectors_are_normalized():
    emb, _ = make_embedder(FakeModels())
    for v in emb.embed_documents(["a", "b", "c"]):
        assert math.sqrt(sum(x * x for x in v)) == pytest.approx(1.0)


def test_normalize_handles_zero_vector():
    assert normalize([0.0, 0.0]) == [0.0, 0.0]


def test_empty_input_makes_no_calls():
    models = FakeModels()
    emb, _ = make_embedder(models)
    assert emb.embed_documents([]) == []
    assert models.calls == []


def test_retries_rate_limit_with_backoff_then_succeeds():
    models = FakeModels(failures=[api_error(429), api_error(503)])
    emb, sleeps = make_embedder(models)
    assert len(emb.embed_documents(["x"])) == 1
    assert len(models.calls) == 3
    assert sleeps == [1.0, 2.0]  # exponential backoff


def test_gives_up_after_max_retries():
    models = FakeModels(failures=[api_error(429)] * 10)
    emb, sleeps = make_embedder(models, max_retries=3)
    with pytest.raises(EmbeddingError, match="after 3 retries"):
        emb.embed_documents(["x"])
    assert len(models.calls) == 4      # first try + 3 retries
    assert sleeps == [1.0, 2.0, 4.0]


def test_non_retryable_error_fails_immediately():
    models = FakeModels(failures=[api_error(400)])
    emb, sleeps = make_embedder(models)
    with pytest.raises(EmbeddingError, match="400"):
        emb.embed_documents(["x"])
    assert len(models.calls) == 1 and sleeps == []


def test_wrong_dimension_is_caught():
    emb, _ = make_embedder(FakeModels(dim=DIM + 1))
    with pytest.raises(EmbeddingError, match="Expected 8 dims"):
        emb.embed_documents(["x"])


def test_missing_embeddings_are_caught():
    emb, _ = make_embedder(FakeModels(drop_one=True))
    with pytest.raises(EmbeddingError, match="Asked for 2"):
        emb.embed_documents(["x", "y"])
