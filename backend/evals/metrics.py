"""Pure functions for scoring retrieval. No network, fully unit-tested."""
from dataclasses import dataclass


@dataclass(frozen=True)
class QueryResult:
    question: str
    expected_page: int | None  # None = off-topic, should NOT be answered
    pages: list[int]           # pages of retrieved chunks, best first
    scores: list[float]        # matching similarity scores

    @property
    def top_score(self) -> float:
        return self.scores[0] if self.scores else 0.0


def rank(r: QueryResult) -> int | None:
    """1-based position of the first chunk from the expected page, or None if missing."""
    for i, p in enumerate(r.pages, start=1):
        if p == r.expected_page:
            return i
    return None


def hit_rate(results: list[QueryResult], k: int) -> float:
    """Share of in-scope questions whose expected page is in the top k."""
    scoped = [r for r in results if r.expected_page is not None]
    hits = [r for r in scoped if (n := rank(r)) is not None and n <= k]
    return len(hits) / len(scoped) if scoped else 0.0


def mrr(results: list[QueryResult]) -> float:
    """Mean reciprocal rank: 1.0 if always first, 0.5 if always second, ..."""
    scoped = [r for r in results if r.expected_page is not None]
    total = sum(1 / n for r in scoped if (n := rank(r)) is not None)
    return total / len(scoped) if scoped else 0.0


@dataclass(frozen=True)
class CutoffRow:
    cutoff: float
    answered: float  # share of in-scope questions that pass the gate (want high)
    blocked: float   # share of off-topic questions stopped by the gate (want high)

    @property
    def balanced(self) -> float:
        return (self.answered + self.blocked) / 2


def sweep(results: list[QueryResult], cutoffs: list[float]) -> list[CutoffRow]:
    scoped = [r.top_score for r in results if r.expected_page is not None]
    off = [r.top_score for r in results if r.expected_page is None]
    rows = []
    for c in cutoffs:
        answered = sum(s >= c for s in scoped) / len(scoped) if scoped else 0.0
        blocked = sum(s < c for s in off) / len(off) if off else 0.0
        rows.append(CutoffRow(round(c, 2), answered, blocked))
    return rows


def best_cutoff(rows: list[CutoffRow]) -> CutoffRow:
    """Highest balanced score; ties go to the LOWER cutoff, because wrongly refusing a
    real question is worse than letting an off-topic one reach the LLM (which can still refuse)."""
    return max(rows, key=lambda r: (round(r.balanced, 6), -r.cutoff))
