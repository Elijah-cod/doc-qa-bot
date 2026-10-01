"""Live Gemini tests. Run with:  python -m pytest -m live"""
import math

import pytest

from app.config import get_settings
from app.embeddings import get_embedder

pytestmark = pytest.mark.live


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b))  # vectors are already normalized


def test_real_vectors_have_expected_shape():
    vecs = get_embedder().embed_documents(["hello world", "second text"])
    assert len(vecs) == 2
    assert all(len(v) == get_settings().embed_dim for v in vecs)
    assert all(math.isclose(math.sqrt(sum(x * x for x in v)), 1.0, rel_tol=1e-6) for v in vecs)


def test_similar_meaning_scores_higher():
    emb = get_embedder()
    kitten, invoice = emb.embed_documents([
        "A kitten is a young cat that loves to play.",
        "Invoice #4471: payment due within 30 days.",
    ])
    q = emb.embed_query("Tell me about cats")
    print(f"\ncat~kitten {cosine(q, kitten):.3f} | cat~invoice {cosine(q, invoice):.3f}")
    assert cosine(q, kitten) > cosine(q, invoice) + 0.1


def test_question_finds_the_answering_passage():
    emb = get_embedder()
    passages = [
        "The project codename is BLUEHERON and it launches in March.",
        "Our office is open Monday to Friday, 9am to 5pm.",
        "Employees get 21 days of paid leave per year.",
    ]
    vecs = emb.embed_documents(passages)
    q = emb.embed_query("What is the codename of the project?")
    scores = [cosine(q, v) for v in vecs]
    print("\nscores:", [round(s, 3) for s in scores])
    assert scores.index(max(scores)) == 0
