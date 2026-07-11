import base64

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.schemas import ExportPdfRequest
from app.services.filename import build_export_filename
from app.services.pdf import export_pdf_result
from app.services.sse import sse_stream

router = APIRouter(prefix="/export", tags=["export"])


def _resolve_filename(body: ExportPdfRequest) -> str:
    if body.filename:
        return body.filename.strip().removesuffix(".pdf")
    if body.title:
        return build_export_filename(
            body.title,
            body.company,
            version=body.version or 1,
        )
    return "cv"


@router.post("/pdf")
def export_pdf(body: ExportPdfRequest):
    filename = _resolve_filename(body)
    try:
        result = export_pdf_result(body.markdown)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(
        content=result.pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )


@router.post("/pdf/stream")
def export_pdf_stream(body: ExportPdfRequest):
    filename = _resolve_filename(body)

    def run(emit):
        import base64

        try:
            def progress(step: str, label: str, pct: int | None = None) -> None:
                emit({"type": "progress", "step": step, "label": label, "pct": pct})

            result = export_pdf_result(body.markdown, progress=progress)
            emit(
                {
                    "type": "complete",
                    "filename": f"{filename}.pdf",
                    "page_count": result.page_count,
                    "pdf_base64": base64.b64encode(result.pdf_bytes).decode("ascii"),
                }
            )
        except HTTPException as exc:
            emit({"type": "error", "message": str(exc.detail)})
        except Exception as exc:
            emit({"type": "error", "message": str(exc)})

    return sse_stream(run)
