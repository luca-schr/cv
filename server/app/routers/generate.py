from fastapi import APIRouter, HTTPException

from app.schemas import GenerateRequest, GenerateResponse
from app.services.generator import generate_cv
from app.services.sse import sse_stream

router = APIRouter(prefix="/generate", tags=["generate"])


def _to_response(result) -> GenerateResponse:
    return GenerateResponse(
        id=result.generation_id,
        title=result.title,
        company=result.company,
        markdown=result.markdown,
        warnings=result.warnings,
        page_count=result.page_count,
        version=result.version,
        filename=result.filename,
    )


@router.post("", response_model=GenerateResponse)
def generate(body: GenerateRequest):
    try:
        result = generate_cv(
            job_text=body.job_text.strip(),
            english=body.english,
            temperature=body.temperature,
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return _to_response(result)


@router.post("/stream")
def generate_stream(body: GenerateRequest):
    payload = body.model_dump()
    payload["job_text"] = body.job_text.strip()

    def run(emit):
        try:
            def progress(step: str, label: str, pct: int | None = None) -> None:
                emit({"type": "progress", "step": step, "label": label, "pct": pct})

            result = generate_cv(
                job_text=payload["job_text"],
                english=payload["english"],
                temperature=payload["temperature"],
                progress=progress,
            )
            emit({"type": "complete", "result": _to_response(result).model_dump()})
        except RuntimeError as exc:
            emit({"type": "error", "message": str(exc)})

    return sse_stream(run)
