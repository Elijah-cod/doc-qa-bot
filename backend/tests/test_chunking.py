import re

from app.chunking import chunk_pages, merge_pieces, split_recursive, split_text
from app.parsing import Page

SENTENCE = "Retrieval augmented generation grounds answers in source text. "
LONG_TEXT = "\n\n".join(SENTENCE * 6 for _ in range(20))  # 20 paragraphs, ~7.6k chars


def words(s: str) -> list[str]:
    return re.findall(r"\w+", s)


def test_split_recursive_loses_nothing():
    pieces = split_recursive(LONG_TEXT, 300)
    assert "".join(pieces) == LONG_TEXT
    assert all(len(p) <= 300 for p in pieces)


def test_split_recursive_hard_cuts_text_without_separators():
    pieces = split_recursive("x" * 1000, 300)
    assert [len(p) for p in pieces] == [300, 300, 300, 100]


def test_short_text_is_one_chunk():
    assert split_text("Just one sentence.") == ["Just one sentence."]


def test_empty_text_gives_no_chunks():
    assert split_text("") == []
    assert split_text("   \n\n  ") == []


def test_chunks_respect_size_limit():
    chunks = split_text(LONG_TEXT, chunk_tokens=100, overlap_tokens=20)  # 400 / 80 chars
    assert len(chunks) > 1
    assert all(len(c) <= 400 for c in chunks)


def test_neighbouring_chunks_overlap():
    chunks = split_text(LONG_TEXT, chunk_tokens=100, overlap_tokens=20)
    for prev, nxt in zip(chunks, chunks[1:]):
        tail = prev[-60:]
        assert any(tail[i:i + 20] in nxt for i in range(0, 40)), "no shared text between neighbours"


def test_no_words_lost_and_order_kept():
    text = " ".join(f"word{i}." for i in range(800))
    chunks = split_text(text, chunk_tokens=50, overlap_tokens=10)
    seen = [w for c in chunks for w in words(c)]
    expected = words(text)
    assert set(seen) == set(expected)            # nothing dropped
    firsts = [expected.index(words(c)[0]) for c in chunks]
    assert firsts == sorted(firsts)              # chunks come out in reading order


def test_merge_prefers_paragraph_boundaries():
    text = ("A" * 150 + ".\n\n") + ("B" * 150 + ".\n\n") + ("C" * 150 + ".")
    chunks = split_text(text, chunk_tokens=80, overlap_tokens=0)  # 320 chars
    assert chunks[0].startswith("A") and chunks[0].rstrip().endswith("B.")
    assert chunks[1].startswith("C")


def test_chunk_pages_tags_pages_and_numbers_globally():
    pages = [Page(1, LONG_TEXT), Page(2, ""), Page(3, "Short last page.")]
    chunks = chunk_pages(pages, chunk_tokens=100, overlap_tokens=20)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert {c.page for c in chunks} == {1, 3}     # blank page 2 produces nothing
    assert chunks[-1].page == 3 and chunks[-1].content == "Short last page."


def test_end_to_end_pdf_to_chunks(make_pdf):
    from app.parsing import parse_pdf
    pdf = make_pdf(["Intro paragraph about cats.", "The project codename is BLUEHERON."])
    chunks = chunk_pages(parse_pdf(pdf))
    hit = [c for c in chunks if "BLUEHERON" in c.content]
    assert len(hit) == 1 and hit[0].page == 2
