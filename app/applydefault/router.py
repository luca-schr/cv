from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.applydefault.service import apply_default

router = APIRouter(prefix="/api/applydefault", tags=["applydefault"])


class ApplyDefaultRequest(BaseModel):
    profile_id: str = Field(min_length=1, max_length=80)
    markdown: str = Field(min_length=20)
    lang: str = "fr"


@router.post("")
def api_apply_default(body: ApplyDefaultRequest):
    try:
        return apply_default(body.profile_id, body.lang, body.markdown)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
