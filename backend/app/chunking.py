"""Step 2b: pages -> overlapping chunks of ~N tokens, each tagged with its page."""
from dataclasses import dataclass

from app.parsing import Page

# Try to split on the biggest natural boundary first; fall back to smaller ones.
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

CHARS_PER_TOKEN = 4  # rough rule of thumb for English text


@dataclass(frozen=True)
class Chunk:
    page: int
    chunk_index: int  # position across the whole document: 0, 1, 2, ...
    content: str


def split_recursive(text: str, max_chars: int, separators: list[str] = SEPARATORS) -> list[str]:
    """Cut text into pieces <= max_chars. Separators stay attached, so ''.join(pieces) == text."""
    if len(text) <= max_chars:
        return [text] if text else []

    sep = next(s for s in separators if s == "" or s in text)
    if sep == "":  # no boundary left: hard cut
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]

    parts = text.split(sep)
    parts = [p + sep for p in parts[:-1]] + [parts[-1]]
    finer = separators[separators.index(sep) + 1 :]

    pieces: list[str] = []
    for part in parts:
        if len(part) <= max_chars:
            if part:
                pieces.append(part)
        else:
            pieces.extend(split_recursive(part, max_chars, finer))
    return pieces


def merge_pieces(pieces: list[str], max_chars: int, overlap_chars: int) -> list[str]:
    """Pack small pieces into chunks up to max_chars; start each new chunk with the
    last ~overlap_chars of the previous one so ideas cut at a boundary aren't lost."""
    chunks: list[str] = []
    window: list[str] = []
    size = 0
    for piece in pieces:
        if window and size + len(piece) > max_chars:
            chunks.append("".join(window))
            # Keep only a tail of the window as overlap, and make room for the new piece.
            while window and (size > overlap_chars or size + len(piece) > max_chars):
                size -= len(window.pop(0))
        window.append(piece)
        size += len(piece)
    if window:
        chunks.append("".join(window))
    return [c.strip() for c in chunks if c.strip()]


def split_text(text: str, chunk_tokens: int = 500, overlap_tokens: int = 50) -> list[str]:
    max_chars = chunk_tokens * CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * CHARS_PER_TOKEN
    return merge_pieces(split_recursive(text, max_chars), max_chars, overlap_chars)


def chunk_pages(pages: list[Page], chunk_tokens: int = 500, overlap_tokens: int = 50) -> list[Chunk]:
    """Chunk each page separately so every chunk has one exact page number."""
    chunks: list[Chunk] = []
    for page in pages:
        for text in split_text(page.text, chunk_tokens, overlap_tokens):
            chunks.append(Chunk(page=page.number, chunk_index=len(chunks), content=text))
    return chunks
