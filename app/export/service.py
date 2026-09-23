from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.export.pdf import export_pdf


class PdfRequest(BaseModel):
    markdown: str = Field(min_length=20)
    filename: str | None = Field(default=None, max_length=140)


def safe_filename(raw: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", (raw or "cv").strip()).strip("-")
    return slug or "cv"


def build_pdf(markdown: str) -> bytes:
    return export_pdf(markdown)
