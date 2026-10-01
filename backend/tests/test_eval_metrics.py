import json
from pathlib import Path

from evals.metrics import QueryResult, best_cutoff, hit_rate, mrr, rank, sweep


def q(expected, pages, top):
    return QueryResult("q", expected, pages, [top] + [0.1] * (len(pages) - 1))


RESULTS = [
    q(2, [2, 1, 3], 0.80),   # rank 1
    q(3, [1, 3, 2], 0.70),   # rank 2
    q(4, [1, 2, 3], 0.65),   # miss
    q(None, [1, 2], 0.55),   # off-topic
    q(None, [3, 1], 0.45),   # off-topic
]


def test_rank():
    assert [rank(r) for r in RESULTS[:3]] == [1, 2, None]


def test_hit_rate_ignores_off_topic():
    assert hit_rate(RESULTS, 1) == 1 / 3
    assert hit_rate(RESULTS, 2) == 2 / 3
    assert hit_rate(RESULTS, 5) == 2 / 3


def test_mrr():
    assert mrr(RESULTS) == (1 + 0.5 + 0) / 3


def test_sweep_and_best_cutoff():
    rows = {r.cutoff: r for r in sweep(RESULTS, [0.5, 0.6, 0.7])}
    assert (rows[0.5].answered, rows[0.5].blocked) == (1.0, 0.5)
    assert (rows[0.6].answered, rows[0.6].blocked) == (1.0, 1.0)
    assert (rows[0.7].answered, rows[0.7].blocked) == (2 / 3, 1.0)
    assert best_cutoff(list(rows.values())).cutoff == 0.6


def test_best_cutoff_tie_prefers_lower():
    rows = sweep([q(1, [1], 0.9), q(None, [1], 0.3)], [0.4, 0.5, 0.6])
    assert best_cutoff(rows).cutoff == 0.4


def test_dataset_is_well_formed():
    data = json.loads((Path(__file__).parents[1] / "evals" / "dataset.json").read_text())
    n_pages = len(data["pages"])
    assert len(data["questions"]) >= 15 and len(data["off_topic"]) >= 5
    for item in data["questions"]:
        assert 1 <= item["page"] <= n_pages
        page_text = data["pages"][item["page"] - 1]
        assert all(e.lower() in page_text.lower() for e in item["expect"]), item["q"]
