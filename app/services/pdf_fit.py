"""Comptage pages PDF."""

from __future__ import annotations

import io


def count_pdf_pages(pdf_bytes: bytes) -> int:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader  # type: ignore[no-redef]

    return len(PdfReader(io.BytesIO(pdf_bytes)).pages)
