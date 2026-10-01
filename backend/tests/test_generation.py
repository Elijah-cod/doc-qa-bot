from types import SimpleNamespace

import pytest
from google.genai import errors

from app.generation import GeminiGenerator, GenerationError


class FakeModels:
    def __init__(self, text="An answer [1].", failures=()):
        self.calls, self.text, self.failures = [], text, list(failures)

    def generate_content(self, *, model, contents, config):
        self.calls.append(SimpleNamespace(model=model, contents=contents, config=config))
        if self.failures:
            raise self.failures.pop(0)
        return SimpleNamespace(text=self.text)


def err(code):
    cls = errors.ClientError if code < 500 else errors.ServerError
    return cls(code, {"error": {"code": code, "message": "x", "status": "S"}})


def make(models, **kw):
    sleeps = []
    return GeminiGenerator(SimpleNamespace(models=models), model="m", sleep=sleeps.append, **kw), sleeps


def test_returns_stripped_text_with_low_temperature():
    models = FakeModels(text="  Hello [1]  \n")
    gen, _ = make(models)
    assert gen.generate("prompt") == "Hello [1]"
    assert models.calls[0].model == "m"
    assert models.calls[0].config.temperature == 0.2


def test_retries_429_then_succeeds():
    models = FakeModels(failures=[errors.ClientError(429, {"error": {"code": 429, "message": "x", "status": "R"}})])
    gen, sleeps = make(models)
    assert gen.generate("p") == "An answer [1]."
    assert sleeps == [1.0]


def test_bad_request_fails_fast():
    models = FakeModels(failures=[errors.ClientError(400, {"error": {"code": 400, "message": "x", "status": "B"}})])
    gen, sleeps = make(models)
    with pytest.raises(GenerationError, match="400"):
        gen.generate("p")
    assert sleeps == []


@pytest.mark.parametrize("text", [None, "", "   "])
def test_empty_answer_is_an_error(text):
    gen, _ = make(FakeModels(text=text))
    with pytest.raises(GenerationError, match="empty"):
        gen.generate("p")


def test_function_calling_disabled():
    models = FakeModels()
    gen, _ = make(models)
    gen.generate("p")
    assert models.calls[0].config.automatic_function_calling.disable is True


def test_overloaded_main_model_falls_back():
    # main model: 503 on every try (1 + 4 retries); fallback succeeds first time
    models = FakeModels(failures=[err(503)] * 5)
    gen, sleeps = make(models, fallback_model="backup")
    assert gen.generate("p") == "An answer [1]."
    assert [c.model for c in models.calls] == ["m"] * 5 + ["backup"]
    assert sleeps == [1.0, 2.0, 4.0, 8.0]


def test_both_models_overloaded_gives_clear_error():
    models = FakeModels(failures=[err(503)] * 10)
    gen, _ = make(models, fallback_model="backup")
    with pytest.raises(GenerationError, match=r"after 4 retries \(503\) on: m, backup"):
        gen.generate("p")


def test_no_fallback_configured():
    models = FakeModels(failures=[err(503)] * 5)
    gen, _ = make(models)
    with pytest.raises(GenerationError, match="on: m."):
        gen.generate("p")
    assert len(models.calls) == 5


def test_bad_request_does_not_fall_back():
    models = FakeModels(failures=[err(404)])
    gen, _ = make(models, fallback_model="backup")
    with pytest.raises(GenerationError, match="404"):
        gen.generate("p")
    assert [c.model for c in models.calls] == ["m"]   # a config error should be loud, not hidden
