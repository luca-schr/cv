import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Profile
from app.schemas import ProfileCreate, ProfileMarkdownRead, ProfileRead, ProfileUpdate
from app.seed import DEFAULT_PROFILE, SEED_PROFILES
from app.services.pdf import export_pdf
from app.services.renderer import build_markdown
from app.services.slugify import build_cv_basename

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _to_read(profile: Profile) -> ProfileRead:
    return ProfileRead(
        id=profile.id,
        name=profile.name,
        is_default=profile.is_default,
        data=json.loads(profile.data),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get("", response_model=list[ProfileRead])
def list_profiles(db: Session = Depends(get_db)):
    return [_to_read(p) for p in db.query(Profile).order_by(Profile.id).all()]


@router.get("/default", response_model=ProfileRead)
def get_default(db: Session = Depends(get_db)):
    return _to_read(get_default_profile(db))


@router.get("/default/markdown", response_model=ProfileMarkdownRead)
def get_default_markdown(db: Session = Depends(get_db)):
    profile = get_default_profile(db)
    data = json.loads(profile.data)
    title = data["header"]["title_default"]
    markdown = build_markdown(data)
    return ProfileMarkdownRead(
        profile_id=profile.id,
        title=title,
        markdown=markdown,
        is_default=True,
    )


@router.get("/default/pdf")
def download_default_pdf(db: Session = Depends(get_db)):
    profile = get_default_profile(db)
    data = json.loads(profile.data)
    title = data["header"]["title_default"]
    markdown = build_markdown(data)
    pdf_bytes = export_pdf(markdown)
    slug = build_cv_basename(title)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{slug}.pdf"'},
    )


@router.patch("/default", response_model=ProfileRead)
def update_default(body: ProfileUpdate, db: Session = Depends(get_db)):
    """Met à jour le profil par défaut en base (persistant entre redémarrages)."""
    profile = get_default_profile(db)
    if body.name is not None:
        profile.name = body.name
    if body.data is not None:
        profile.data = json.dumps(body.data, ensure_ascii=False)
    db.commit()
    db.refresh(profile)
    return _to_read(profile)


def sync_default_from_seed(db: Session) -> Profile:
    """Réinjecte les profils seed (fullstack par défaut + chef de projet)."""
    default = get_default_profile(db)
    default.name = "Développeur fullstack"
    default.data = json.dumps(DEFAULT_PROFILE, ensure_ascii=False)
    db.commit()
    db.refresh(default)
    _sync_extra_seed_profiles(db)
    return default


def _profile_key(raw_data: str) -> str | None:
    try:
        data = json.loads(raw_data)
    except json.JSONDecodeError:
        return None
    key = data.get("key")
    return str(key) if key else None


def _sync_extra_seed_profiles(db: Session) -> None:
    existing_by_key: dict[str, Profile] = {}
    for profile in db.query(Profile).all():
        key = _profile_key(profile.data)
        if key:
            existing_by_key[key] = profile

    for name, data, is_default in SEED_PROFILES:
        if is_default:
            continue
        key = data.get("key")
        payload = json.dumps(data, ensure_ascii=False)
        current = existing_by_key.get(key)
        if current:
            current.name = name
            current.data = payload
            continue
        db.add(Profile(name=name, data=payload, is_default=False))
    db.commit()


@router.post("/default/sync-seed", response_model=ProfileRead)
def sync_default_from_seed_endpoint(db: Session = Depends(get_db)):
    return _to_read(sync_default_from_seed(db))


@router.get("/{profile_id}", response_model=ProfileRead)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(404, "Profil introuvable")
    return _to_read(profile)


@router.get("/{profile_id}/markdown", response_model=ProfileMarkdownRead)
def get_profile_markdown(profile_id: int, db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(404, "Profil introuvable")
    data = json.loads(profile.data)
    title = data["header"]["title_default"]
    markdown = build_markdown(data)
    return ProfileMarkdownRead(
        profile_id=profile.id,
        title=title,
        markdown=markdown,
        is_default=profile.is_default,
    )


@router.post("", response_model=ProfileRead, status_code=201)
def create_profile(body: ProfileCreate, db: Session = Depends(get_db)):
    if body.is_default:
        db.query(Profile).update({Profile.is_default: False})
    profile = Profile(
        name=body.name,
        data=json.dumps(body.data, ensure_ascii=False),
        is_default=body.is_default,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _to_read(profile)


@router.patch("/{profile_id}", response_model=ProfileRead)
def update_profile(profile_id: int, body: ProfileUpdate, db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(404, "Profil introuvable")
    if body.name is not None:
        profile.name = body.name
    if body.data is not None:
        profile.data = json.dumps(body.data, ensure_ascii=False)
    if body.is_default is not None:
        if body.is_default:
            db.query(Profile).update({Profile.is_default: False})
        profile.is_default = body.is_default
    db.commit()
    db.refresh(profile)
    return _to_read(profile)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(404, "Profil introuvable")
    db.delete(profile)
    db.commit()


def get_default_profile(db: Session) -> Profile:
    profile = db.query(Profile).filter(Profile.is_default.is_(True)).first()
    if not profile:
        profile = Profile(
            name="Développeur fullstack",
            data=json.dumps(DEFAULT_PROFILE, ensure_ascii=False),
            is_default=True,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile
