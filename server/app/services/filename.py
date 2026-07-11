"""Nommage des exports : [titre]-[entreprise|master]-[vN si plusieurs]."""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy.orm import Session

from app.models import Generation
from app.services.sanitize import normalize_name


def slug_part(value: str, *, max_len: int = 48) -> str:
    text = normalize_name(value)
    if not text:
        return ""
    return text[:max_len].rstrip("-")


def build_export_filename(
    title: str,
    company: str | None,
    *,
    version: int = 1,
) -> str:
    title_slug = slug_part(title) or "cv"
    org_slug = slug_part(company) if company else "master"
    base = f"{title_slug}-{org_slug}"
    if version > 1:
        return f"{base}-v{version}"
    return base


def next_generation_version(
    db: Session,
    *,
    profile_id: int,
    title: str,
    company: str | None,
) -> int:
    query = db.query(Generation).filter(
        Generation.profile_id == profile_id,
        Generation.title == title,
    )
    if company is None:
        query = query.filter(Generation.company.is_(None))
    else:
        query = query.filter(Generation.company == company)
    return query.count() + 1
