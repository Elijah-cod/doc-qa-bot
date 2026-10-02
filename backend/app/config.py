from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All config comes from environment variables / backend/.env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Secrets (required at runtime, not at import time)
    gemini_api_key: str = ""
    supabase_url: str = ""
    supabase_service_key: str = ""

    # CORS: comma-separated list of allowed frontend origins
    allowed_origins: str = "http://localhost:3000"
    # Optional regex for extra origins, e.g. Vercel preview URLs: https://doc-qa-.*\.vercel\.app
    allowed_origin_regex: str = ""

    # Models (override in .env without touching code)
    embed_model: str = "gemini-embedding-001"
    embed_dim: int = 768  # must match vector(768) in sql/001_init.sql
    embed_batch_size: int = 100  # texts per Gemini request
    gen_model: str = "gemini-flash-latest"  # alias that tracks the newest Flash model
    gen_fallback_model: str = "gemini-flash-lite-latest"  # used if the main model is overloaded; "" disables

    # Ingestion
    chunk_tokens: int = 500
    chunk_overlap_tokens: int = 50
    max_pages: int = 200
    max_upload_mb: int = 10

    # Abuse protection (per client IP, per hour; 0 disables)
    upload_limit_per_hour: int = 10
    ask_limit_per_hour: int = 60

    # Retrieval
    top_k: int = 5
    score_cutoff: float = 0.56  # from evals/results.md: keeps 100% of real questions, blocks 83% off-topic

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
