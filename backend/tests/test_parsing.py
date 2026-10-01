import pytest

from app.parsing import PDFParseError, clean_block, parse_pdf


def test_pages_numbered_from_one_and_text_extracted(make_pdf):
    pages = parse_pdf(make_pdf(["Hello from page one.", "Greetings from page two."]))
    assert [p.number for p in pages] == [1, 2]
    assert "page one" in pages[0].text
    assert "page two" in pages[1].text


def test_blank_page_kept_as_empty_so_numbers_stay_correct(make_pdf):
    pages = parse_pdf(make_pdf(["First.", "", "Third."]))
    assert [p.number for p in pages] == [1, 2, 3]
    assert pages[1].text == ""
    assert "Third" in pages[2].text


def test_pdf_with_no_text_is_rejected(make_pdf):
    with pytest.raises(PDFParseError, match="scanned"):
        parse_pdf(make_pdf(["", ""]))


def test_non_pdf_bytes_rejected():
    with pytest.raises(PDFParseError, match="not a readable PDF"):
        parse_pdf(b"this is just a text file")


def test_page_limit_enforced(make_pdf):
    with pytest.raises(PDFParseError, match="limit is 2"):
        parse_pdf(make_pdf(["a", "b", "c"]), max_pages=2)


def test_clean_block_fixes_wraps_hyphens_and_spaces():
    raw = "Retrieval-aug-\nmented genera-\ntion\nworks well.   "
    assert clean_block(raw) == "Retrieval-augmented generation works well."
