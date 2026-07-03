from fastapi import APIRouter
from fastapi.responses import Response

from app.schemas import MarkdownPdfRequest
from app.services.pdf import export_pdf
from app.services.slugify import slugify

router = APIRouter(prefix="/export", tags=["export"])


def _safe_filename(raw: str) -> str:
    name = slugify(raw or "cv", max_len=60)
    return name or "cv"


@router.post("/pdf")
def pdf_from_markdown(body: MarkdownPdfRequest):
    pdf_bytes = export_pdf(body.markdown)
    slug = _safe_filename(body.filename or "cv")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{slug}.pdf"'},
    )
