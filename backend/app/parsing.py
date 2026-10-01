"""Step 2a: PDF bytes -> list of pages with clean text."""
import re
from dataclasses import dataclass

import pymupdf


class PDFParseError(ValueError):
    """The upload can't be turned into text (not a PDF, encrypted, scanned, too long)."""


@dataclass(frozen=True)
class Page:
    number: int  # 1-based, as humans count pages
    text: str    # paragraphs separated by blank lines


def clean_block(text: str) -> str:
    """Tidy one PDF text block (roughly one paragraph)."""
    text = text.replace(" ", " ")             # non-breaking spaces
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)   # re-join words hyphenated across lines
    text = text.replace("\n", " ")                 # line wraps inside a paragraph
    return re.sub(r"\s+", " ", text).strip()


def parse_pdf(data: bytes, max_pages: int | None = None) -> list[Page]:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as e:
        raise PDFParseError("File is not a readable PDF.") from e

    with doc:
        if doc.needs_pass:
            raise PDFParseError("PDF is password-protected.")
        if max_pages is not None and doc.page_count > max_pages:
            raise PDFParseError(f"PDF has {doc.page_count} pages; the limit is {max_pages}.")

        pages = []
        for i, page in enumerate(doc):
            # Each block is (x0, y0, x1, y1, text, block_no, block_type); type 0 = text.
            blocks = page.get_text("blocks", sort=True)
            paragraphs = [clean_block(b[4]) for b in blocks if b[6] == 0]
            text = "\n\n".join(p for p in paragraphs if p)
            pages.append(Page(number=i + 1, text=text))

    if not any(p.text for p in pages):
        raise PDFParseError("No extractable text. Is this a scanned PDF? (OCR isn't supported.)")
    return pages
