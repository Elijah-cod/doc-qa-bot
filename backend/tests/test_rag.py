import pytest

from app.config import Settings
from app.rag import (NOT_FOUND, DocumentNotFound, answer_question, build_prompt, cited_numbers,
                     passes_gate)
from app.store import RetrievedChunk
from tests.fakes import FakeEmbedder, FakeGenerator, InMemoryStore


def chunk(score, page=1, content="text", i=0):
    return RetrievedChunk(id=i, page=page, chunk_index=i, content=content, score=score)


def test_prompt_numbers_sources_with_pages():
    p = build_prompt("  What is X?  ", [chunk(0.9, page=3, content="X is a cat."), chunk(0.8, page=7, content="Y.")])
    assert "[1] (page 3)\nX is a cat." in p
    assert "[2] (page 7)\nY." in p
    assert "Question: What is X?\nAnswer:" in p
    assert NOT_FOUND in p                    # model is told the exact refusal sentence
    assert "ONLY the numbered sources" in p


@pytest.mark.parametrize("scores,cutoff,expected", [
    ([], 0.5, False),            # nothing retrieved
    ([0.3, 0.2], 0.5, False),    # best is below cutoff
    ([0.5], 0.5, True),          # exactly at cutoff passes
    ([0.8, 0.1], 0.5, True),
])
def test_score_gate(scores, cutoff, expected):
    assert passes_gate([chunk(s) for s in scores], cutoff) is expected


def test_cited_numbers_ignores_invalid():
    assert cited_numbers("A [1], B [3][2], fake [9], [0].", n_sources=3) == {1, 2, 3}
    assert cited_numbers("no citations", n_sources=3) == set()


@pytest.fixture
def setup():
    store = InMemoryStore()
    emb = FakeEmbedder()
    texts = ["Cats are small furry pets.", "The project codename is BLUEHERON.", "Lunch is at noon."]
    from app.chunking import Chunk
    chunks = [Chunk(page=i + 1, chunk_index=i, content=t) for i, t in enumerate(texts)]
    store.insert_chunks("doc-1", chunks, emb.embed_documents(texts))
    return store, emb


def test_relevant_question_calls_llm_with_best_chunk_first(setup):
    store, emb = setup
    gen = FakeGenerator()
    r = answer_question("What is the project codename?", "doc-1", embedder=emb, store=store,
                        generator=gen, settings=Settings(_env_file=None, score_cutoff=0.3, top_k=2))
    assert r.grounded is True
    assert r.answer == gen.answer
    assert len(r.sources) == 2                                  # top_k respected
    assert "BLUEHERON" in r.sources[0].chunk.content and r.sources[0].chunk.page == 2
    assert r.sources[0].cited is True and r.sources[1].cited is False
    assert "[1] (page 2)\nThe project codename is BLUEHERON." in gen.prompts[0]
    assert emb.calls[-1] == ("query", 1)                        # question used the QUERY task type


def test_irrelevant_question_skips_llm(setup):
    store, emb = setup
    gen = FakeGenerator()
    r = answer_question("Quantum chromodynamics?", "doc-1", embedder=emb, store=store,
                        generator=gen, settings=Settings(_env_file=None, score_cutoff=0.3))
    assert r.grounded is False
    assert r.answer == NOT_FOUND
    assert gen.prompts == []                                    # no LLM call
    assert r.sources                                            # still show closest matches


def test_unknown_document_raises(setup):
    store, emb = setup
    with pytest.raises(DocumentNotFound):
        answer_question("anything", "no-such-doc", embedder=emb, store=store,
                        generator=FakeGenerator(), settings=Settings(_env_file=None))
