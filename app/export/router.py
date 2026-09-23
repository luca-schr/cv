from fastapi import APIRouter
from fastapi.responses import Response

from app.export.service import PdfRequest, build_pdf, safe_filename

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/pdf")
def pdf_from_markdown(body: PdfRequest):
    pdf_bytes = build_pdf(body.markdown)
    slug = safe_filename(body.filename or "cv")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{slug}.pdf"'},
    )
