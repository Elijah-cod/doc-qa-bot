"""The Step 6 smoke test: real PDF -> real Gemini -> real Supabase -> real answer.
Run with:  python -m pytest -m live -s"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rag import NOT_FOUND

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def ctx():
    from tests.conftest import build_pdf
    client = TestClient(app)
    pdf = build_pdf([
        "Our company offers employees 21 days of paid leave per year, plus public holidays.",
        "The secret project codename is BLUEHERON. It is scheduled to launch in March.",
        "The office cafeteria serves lunch between 12pm and 2pm on weekdays.",
    ])
    doc_id = client.post("/upload", files={"file": ("live.pdf", pdf, "application/pdf")}).json()["doc_id"]
    yield client, doc_id
    client.delete(f"/documents/{doc_id}")


def ask(client, doc_id, q):
    r = client.post("/ask", json={"doc_id": doc_id, "question": q})
    assert r.status_code == 200, r.text
    body = r.json()
    print(f"\nQ: {q}\nA: {body['answer']}\nscores: {[s['score'] for s in body['sources']]}")
    return body


def test_answers_from_the_right_page_with_citation(ctx):
    body = ask(*ctx, "What is the project's codename?")
    assert body["grounded"] is True
    assert "BLUEHERON" in body["answer"]
    assert body["sources"][0]["page"] == 2
    assert any(s["cited"] for s in body["sources"])


def test_off_topic_question_is_refused(ctx):
    body = ask(*ctx, "What is the capital of France?")
    # Either the score gate stops it, or the model follows the rule and refuses.
    assert NOT_FOUND in body["answer"]
    assert "Paris" not in body["answer"]
