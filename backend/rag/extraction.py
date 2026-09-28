from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader

from .security import sanitize_chunk_text


class ExtractionError(ValueError):
    pass


def extract_txt(data: bytes) -> list[tuple[int | None, str]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1", errors="replace")
    text = sanitize_chunk_text(text.replace("\n", " \n "))
    if not text:
        raise ExtractionError("The text file is empty.")
    return [(1, text)]


def extract_pdf(data: bytes) -> list[tuple[int | None, str]]:
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as error:
        raise ExtractionError(f"Could not read PDF: {error}") from error
    pages: list[tuple[int | None, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            raw = page.extract_text() or ""
        except Exception:
            raw = ""
        text = sanitize_chunk_text(raw.replace("\n", " "))
        if text:
            pages.append((index, text))
    if not pages:
        raise ExtractionError("No extractable text found in this PDF.")
    return pages


def extract_pages(filename: str, data: bytes) -> list[tuple[int | None, str]]:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(data)
    if suffix == ".txt":
        return extract_txt(data)
    raise ExtractionError("Unsupported file type. Upload a PDF or TXT file.")
