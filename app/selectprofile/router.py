from fastapi import APIRouter, HTTPException

from app.selectprofile.service import get_profile_detail, list_profiles

router = APIRouter(prefix="/api/selectprofile", tags=["selectprofile"])


@router.get("")
def api_list_profiles():
    return list_profiles()


@router.get("/{profile_id}")
def api_read_profile(profile_id: str, lang: str = "fr"):
    try:
        return get_profile_detail(profile_id, lang)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
