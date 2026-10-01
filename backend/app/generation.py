"""Step 5b: prompt -> answer text with Gemini."""
import time
from collections.abc import Callable
from functools import lru_cache
from typing import Protocol

from google import genai
from google.genai import errors, types

from app.config import get_settings
from app.embeddings import RETRYABLE_CODES


class GenerationError(RuntimeError):
    """The model call failed for good, or returned no text (e.g. blocked by safety filters)."""


class Generator(Protocol):
    def generate(self, prompt: str) -> str: ...


class _StillFailing(Exception):
    """Internal: a model kept returning retryable errors (e.g. 503 overloaded)."""


class GeminiGenerator:
    def __init__(self, client: genai.Client, model: str, fallback_model: str | None = None,
                 temperature: float = 0.2, max_retries: int = 4, base_delay: float = 1.0,
                 sleep: Callable[[float], None] = time.sleep):
        self.client = client
        # Try the main model first; if Google says it's overloaded, try the fallback.
        self.models = [m for m in (model, fallback_model) if m]
        self.temperature = temperature  # low = stick to the sources, less creative wording
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.sleep = sleep
        self.config = types.GenerateContentConfig(
            temperature=temperature,
            # We never give the model tools; turning this off also silences an SDK warning.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    def generate(self, prompt: str) -> str:
        last: Exception | None = None
        for model in self.models:
            try:
                response = self._call_with_retry(model, prompt)
            except _StillFailing as e:
                last = e.__cause__
                continue  # overloaded -> fall back to the next model
            text = (response.text or "").strip()
            if not text:
                raise GenerationError("Gemini returned an empty answer (possibly blocked).")
            return text
        code = getattr(last, "code", "?")
        raise GenerationError(
            f"Gemini still failing after {self.max_retries} retries ({code}) on: {', '.join(self.models)}."
        ) from last

    def _call_with_retry(self, model: str, prompt: str):
        for attempt in range(self.max_retries + 1):
            try:
                return self.client.models.generate_content(model=model, contents=prompt, config=self.config)
            except errors.APIError as e:
                if e.code not in RETRYABLE_CODES:
                    raise GenerationError(f"Gemini rejected the request ({e.code} {e.status}).") from e
                if attempt == self.max_retries:
                    raise _StillFailing() from e
                self.sleep(min(self.base_delay * 2**attempt, 30.0))
        raise AssertionError("unreachable")


@lru_cache
def get_generator() -> GeminiGenerator:
    s = get_settings()
    if not s.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY missing from .env")
    return GeminiGenerator(client=genai.Client(api_key=s.gemini_api_key), model=s.gen_model,
                           fallback_model=s.gen_fallback_model or None)
