"""Fusion catégories par nom normalisé."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Category, Skill
from app.services.sanitize import normalize_name


def get_or_create_category(
    db: Session,
    *,
    profile_id: int,
    name: str,
    source: str,
    sort_order: int = 0,
) -> Category:
    norm = normalize_name(name)
    existing = (
        db.query(Category)
        .filter(Category.profile_id == profile_id, Category.name_normalized == norm)
        .first()
    )
    if existing:
        return existing
    cat = Category(
        profile_id=profile_id,
        name=name.strip(),
        name_normalized=norm,
        source=source,
        sort_order=sort_order,
    )
    db.add(cat)
    db.flush()
    return cat


def upsert_skill(
    db: Session,
    *,
    profile_id: int,
    category: Category,
    name: str,
    level: int | None,
    source: str,
) -> Skill | None:
    norm = normalize_name(name)
    if not norm:
        return None
    existing = (
        db.query(Skill)
        .filter(Skill.profile_id == profile_id, Skill.name_normalized == norm)
        .first()
    )
    if existing:
        if existing.level is None and level is not None:
            existing.level = level
        return existing
    skill = Skill(
        profile_id=profile_id,
        category_id=category.id,
        name=name.strip(),
        name_normalized=norm,
        level=level,
        source=source,
    )
    db.add(skill)
    db.flush()
    return skill


def prune_empty_categories(db: Session, profile_id: int) -> None:
    cats = db.query(Category).filter(Category.profile_id == profile_id).all()
    for cat in cats:
        if not cat.skills:
            db.delete(cat)
