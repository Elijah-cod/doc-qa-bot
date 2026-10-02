import pymupdf
import pytest

from app.ratelimit import reset_limits


def build_pdf(pages: list[str]) -> bytes:
    """Make a real PDF in memory. Each string is one page; '' makes a blank page."""
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_textbox(pymupdf.Rect(72, 72, 540, 770), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def make_pdf():
    return build_pdf


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Rate-limit counters are global; start every test with a clean slate."""
    reset_limits()
    yield
    reset_limits()
