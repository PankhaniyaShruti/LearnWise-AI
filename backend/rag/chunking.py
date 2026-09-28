from __future__ import annotations

import uuid
from typing import Any


def chunk_pages(
    pages: list[tuple[int | None, str]],
    *,
    document_id: str,
    user_email: str,
    filename: str,
    chunk_size: int = 900,
    overlap: int = 140,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    index = 0
    for page_number, text in pages:
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            piece = text[start:end].strip()
            if piece:
                chunks.append(
                    {
                        "chunk_id": str(uuid.uuid4()),
                        "document_id": document_id,
                        "user_email": user_email,
                        "chunk_index": index,
                        "page_number": page_number,
                        "text": piece,
                        "metadata": {
                            "filename": filename,
                            "char_start": start,
                            "char_end": end,
                        },
                    }
                )
                index += 1
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks
