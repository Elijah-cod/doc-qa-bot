from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache
def get_supabase() -> Client:
    s = get_settings()
    if not s.supabase_url or not s.supabase_service_key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY missing from .env")
    return create_client(s.supabase_url, s.supabase_service_key)


def to_pgvector(values: list[float]) -> str:
    """pgvector's text format: '[0.1,0.2,...]'. PostgREST passes it straight through."""
    return "[" + ",".join(f"{v:.8g}" for v in values) + "]"
