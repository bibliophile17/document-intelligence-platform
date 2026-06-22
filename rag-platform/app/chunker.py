"""
chunker.py
Splits long document text into overlapping chunks suitable for embedding.
Overlap preserves context across chunk boundaries so answers don't lose
information that falls near a split point.
"""

from typing import List


def chunk_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> List[str]:
    """
    Split text into overlapping chunks by character count.

    chunk_size: target number of characters per chunk
    chunk_overlap: number of characters repeated between consecutive chunks
    """
    if not text or not text.strip():
        return []

    # Normalize whitespace
    text = " ".join(text.split())

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size

        # Try to break on a sentence or word boundary instead of mid-word
        if end < text_len:
            boundary = text.rfind(". ", start, end)
            if boundary == -1 or boundary < start + (chunk_size // 2):
                boundary = text.rfind(" ", start, end)
            if boundary != -1 and boundary > start:
                end = boundary + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break

        start = end - chunk_overlap

    return chunks
