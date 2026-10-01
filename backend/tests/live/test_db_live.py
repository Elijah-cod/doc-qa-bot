"""Live test against your real Supabase project. Run with:  python -m pytest -m live"""
import uuid

import pytest
from postgrest.exceptions import APIError

from app.config import get_settings
from app.db import get_supabase, to_pgvector

pytestmark = pytest.mark.live


def unit_vec(dim: int, *hot: int) -> list[float]:
    """Vector with 1.0 at the given positions, 0 elsewhere."""
    v = [0.0] * dim
    for i in hot:
        v[i] = 1.0
    return v


@pytest.fixture(scope="module", autouse=True)
def schema_ready():
    """Fail fast with one clear message if sql/001_init.sql hasn't been applied."""
    try:
        get_supabase().table("chunks").select("id").limit(1).execute()
    except APIError as e:
        if getattr(e, "code", None) == "PGRST205":
            pytest.fail(
                "Table 'chunks' not visible to the Supabase API. Run backend/sql/001_init.sql "
                "in the SQL Editor of the project in SUPABASE_URL, then: notify pgrst, 'reload schema';",
                pytrace=False,
            )
        raise


@pytest.fixture
def doc_id():
    """A throwaway document id; its rows are deleted after the test."""
    did = str(uuid.uuid4())
    yield did
    get_supabase().table("chunks").delete().eq("doc_id", did).execute()


def test_match_chunks_returns_nearest_first(doc_id):
    db = get_supabase()
    dim = get_settings().embed_dim

    rows = [
        {"doc_id": doc_id, "page": 1, "chunk_index": 0, "content": "A", "embedding": to_pgvector(unit_vec(dim, 0))},
        {"doc_id": doc_id, "page": 2, "chunk_index": 1, "content": "B", "embedding": to_pgvector(unit_vec(dim, 1))},
        {"doc_id": doc_id, "page": 3, "chunk_index": 2, "content": "C", "embedding": to_pgvector(unit_vec(dim, 2))},
    ]
    db.table("chunks").insert(rows).execute()

    # Query leans heavily toward A, a little toward B, not at all toward C.
    query = unit_vec(dim)
    query[0], query[1] = 0.9, 0.3

    res = db.rpc("match_chunks", {"query_embedding": to_pgvector(query), "p_doc_id": doc_id, "match_count": 3}).execute()
    got = res.data

    assert [r["content"] for r in got] == ["A", "B", "C"]
    assert got[0]["page"] == 1
    assert got[0]["score"] > got[1]["score"] > got[2]["score"]
    assert got[2]["score"] == pytest.approx(0.0, abs=1e-6)  # orthogonal = unrelated


def test_match_chunks_is_scoped_to_doc(doc_id):
    db = get_supabase()
    dim = get_settings().embed_dim
    other = str(uuid.uuid4())
    try:
        db.table("chunks").insert([
            {"doc_id": doc_id, "page": 1, "chunk_index": 0, "content": "mine", "embedding": to_pgvector(unit_vec(dim, 0))},
            {"doc_id": other, "page": 1, "chunk_index": 0, "content": "theirs", "embedding": to_pgvector(unit_vec(dim, 0))},
        ]).execute()
        res = db.rpc("match_chunks", {"query_embedding": to_pgvector(unit_vec(dim, 0)), "p_doc_id": doc_id}).execute()
        assert [r["content"] for r in res.data] == ["mine"]
    finally:
        db.table("chunks").delete().eq("doc_id", other).execute()
