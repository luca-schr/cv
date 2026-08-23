from __future__ import annotations

import io


def count_pdf_pages(pdf_bytes: bytes) -> int:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader  # type: ignore[no-redef]

    n = len(PdfReader(io.BytesIO(pdf_bytes)).pages)
    if n < 1:
        raise ValueError(f"Comptage pages invalide: {n}")
    return n
