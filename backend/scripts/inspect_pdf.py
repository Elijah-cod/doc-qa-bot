"""Debug helper: see how a PDF gets parsed and chunked.

Usage (from backend/):
    python scripts/inspect_pdf.py path/to/file.pdf          # summary + first 3 chunks
    python scripts/inspect_pdf.py path/to/file.pdf --all    # print every chunk
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `app` imports work

from app.chunking import chunk_pages  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.parsing import PDFParseError, parse_pdf  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = Path(sys.argv[1]).expanduser()
    if not path.is_file():
        sys.exit(f"File not found: {path}")

    s = get_settings()
    try:
        pages = parse_pdf(path.read_bytes(), max_pages=s.max_pages)
    except PDFParseError as e:
        sys.exit(f"Could not parse: {e}")

    chunks = chunk_pages(pages, s.chunk_tokens, s.chunk_overlap_tokens)
    sizes = [len(c.content) for c in chunks]
    empty = [p.number for p in pages if not p.text]

    print(f"{path.name}: {len(pages)} pages, {len(chunks)} chunks")
    print(f"chunk size (chars): min {min(sizes)}, avg {sum(sizes) // len(sizes)}, max {max(sizes)}")
    if empty:
        print(f"pages with no text: {empty}")

    show = chunks if "--all" in sys.argv else chunks[:3]
    for c in show:
        print(f"\n--- chunk {c.chunk_index} | page {c.page} | {len(c.content)} chars ---")
        print(c.content)
    if len(show) < len(chunks):
        print(f"\n... {len(chunks) - len(show)} more (use --all)")


if __name__ == "__main__":
    main()
