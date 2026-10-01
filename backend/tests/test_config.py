from app.config import Settings
from app.db import to_pgvector


def test_defaults_match_schema():
    s = Settings(_env_file=None)
    assert s.embed_dim == 768  # keep in sync with vector(768) in sql/001_init.sql
    assert s.top_k == 5


def test_env_vars_override(monkeypatch):
    monkeypatch.setenv("TOP_K", "8")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000, https://my-app.vercel.app")
    s = Settings(_env_file=None)
    assert s.top_k == 8
    assert s.origins == ["http://localhost:3000", "https://my-app.vercel.app"]


def test_to_pgvector_format():
    assert to_pgvector([1.0, 0.0, -0.5]) == "[1,0,-0.5]"
