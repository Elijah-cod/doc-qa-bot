"""Step 7: measure retrieval quality and pick SCORE_CUTOFF from data.

Usage (from backend/):
    python scripts/run_eval.py             # real Gemini + Supabase, retrieval only (cheap)
    python scripts/run_eval.py --answers   # also generate answers and check them (uses LLM quota)
    python scripts/run_eval.py --fake      # offline dry run with fake embedder/store
Writes a markdown report to evals/results.md.
"""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pymupdf  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.ingest import ingest_pdf  # noqa: E402
from app.rag import NOT_FOUND, answer_question  # noqa: E402
from evals.metrics import QueryResult, best_cutoff, hit_rate, mrr, rank, sweep  # noqa: E402


def build_pdf(pages: list[str]) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        doc.new_page().insert_textbox(pymupdf.Rect(72, 72, 540, 770), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def main() -> None:
    fake = "--fake" in sys.argv
    with_answers = "--answers" in sys.argv
    settings = get_settings()
    data = json.loads((ROOT / "evals" / "dataset.json").read_text())

    if fake:
        from tests.fakes import FakeEmbedder, FakeGenerator, InMemoryStore
        embedder, store, generator = FakeEmbedder(), InMemoryStore(), FakeGenerator()
    else:
        from app.embeddings import get_embedder
        from app.generation import get_generator
        from app.store import get_store
        embedder, store = get_embedder(), get_store()
        generator = get_generator() if with_answers else None

    k = settings.top_k
    print(f"Ingesting {len(data['pages'])}-page test document...")
    doc_id = ingest_pdf(build_pdf(data["pages"]), embedder=embedder, store=store, settings=settings).doc_id

    try:
        cases = [(q["q"], q["page"], q["expect"]) for q in data["questions"]]
        cases += [(q, None, None) for q in data["off_topic"]]

        results: list[QueryResult] = []
        answer_rows = []
        for question, page, expect in cases:
            hits = store.match(doc_id, embedder.embed_query(question), k)
            r = QueryResult(question, page, [h.page for h in hits], [h.score for h in hits])
            results.append(r)
            mark = "-" if page is None else (f"#{rank(r)}" if rank(r) else "MISS")
            print(f"  {mark:>4}  top={r.top_score:.3f}  {question}")

            if with_answers:
                ans = answer_question(question, doc_id, embedder=embedder, store=store,
                                      generator=generator, settings=settings).answer
                ok = (NOT_FOUND in ans) if page is None else all(e.lower() in ans.lower() for e in expect)
                answer_rows.append((question, ok, ans))
    finally:
        store.delete_document(doc_id)

    cutoffs = [c / 100 for c in range(40, 82, 2)]
    rows = sweep(results, cutoffs)
    best = best_cutoff(rows)
    scoped = [r for r in results if r.expected_page is not None]
    off = [r for r in results if r.expected_page is None]

    lines = [
        "# Retrieval eval",
        "",
        f"_{date.today()} · embed model `{settings.embed_model}` ({settings.embed_dim} dims) · "
        f"chunk {settings.chunk_tokens} tok · top_k {k}{' · FAKE run' if fake else ''}_",
        "",
        f"{len(scoped)} answerable questions, {len(off)} off-topic questions, fictional 6-page handbook.",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Hit rate @1 | {hit_rate(results, 1):.0%} |",
        f"| Hit rate @{k} | {hit_rate(results, k):.0%} |",
        f"| MRR | {mrr(results):.3f} |",
        f"| Top score, answerable (min / avg) | {min(r.top_score for r in scoped):.3f} / "
        f"{sum(r.top_score for r in scoped) / len(scoped):.3f} |",
        f"| Top score, off-topic (max / avg) | {max(r.top_score for r in off):.3f} / "
        f"{sum(r.top_score for r in off) / len(off):.3f} |",
        "",
        f"**Recommended `SCORE_CUTOFF={best.cutoff}`**: answers {best.answered:.0%} of real questions, "
        f"blocks {best.blocked:.0%} of off-topic ones. (Current setting: {settings.score_cutoff})",
        "",
        "| Cutoff | Real questions answered | Off-topic blocked |",
        "|---|---|---|",
    ]
    lines += [f"| {r.cutoff:.2f}{' ←' if r is best else ''} | {r.answered:.0%} | {r.blocked:.0%} |" for r in rows]

    lines += ["", "## Off-topic top scores", "",
              "Highest first. Anything at or above the cutoff reaches the LLM, which must refuse on its own.", ""]
    lines += [f"- {r.top_score:.3f} {'(passes gate) ' if r.top_score >= settings.score_cutoff else ''}{r.question}"
              for r in sorted(off, key=lambda r: r.top_score, reverse=True)]

    misses = [r for r in scoped if rank(r) != 1]
    if misses:
        lines += ["", "## Not ranked first", ""]
        lines += [f"- {r.question} (expected p{r.expected_page}, got {r.pages})" for r in misses]

    if with_answers:
        passed = sum(ok for _, ok, _ in answer_rows)
        lines += ["", f"## Answers: {passed}/{len(answer_rows)} correct", "",
                  "| | Question | Answer |", "|---|---|---|"]
        lines += [f"| {'✅' if ok else '❌'} | {q} | {a.replace(chr(10), ' ')[:160]} |" for q, ok, a in answer_rows]

    report = "\n".join(lines) + "\n"
    out = ROOT / "evals" / ("results_fake.md" if fake else "results.md")
    out.write_text(report)
    print("\n" + report + f"\nSaved to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
