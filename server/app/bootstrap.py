"""Initialisation profil + skills + subskills en base."""

from __future__ import annotations

import json

from sqlalchemy import nulls_last
from sqlalchemy.orm import Session

from app.models import Category, Profile, Skill, Subskill
from app.seed import DEFAULT_COMPETENCES, DEFAULT_PROFILE_DATA, DEFAULT_SUBSKILLS, PREFERRED_TECH_NORMALIZED
from app.services.category_merge import get_or_create_category, upsert_skill
from app.services.subskills import (
    reconcile_profile_skills,
    seed_subskills_for_profile,
    subskills_by_skill_id,
)


def _expected_subskill_count() -> int:
    return sum(len(items) for items in DEFAULT_SUBSKILLS.values())


def _needs_subskill_seed(db: Session, profile_id: int) -> bool:
    count = db.query(Subskill).filter(Subskill.profile_id == profile_id).count()
    return count < _expected_subskill_count()


def seed_profile_if_needed(db: Session) -> Profile:
    profile = db.query(Profile).filter(Profile.is_default.is_(True)).first()
    if profile:
        has_cats = db.query(Category).filter(Category.profile_id == profile.id).count() > 0
        if not has_cats:
            _seed_skills(db, profile)
            reconcile_profile_skills(db, profile.id)
            seed_subskills_for_profile(db, profile.id)
        elif _needs_subskill_seed(db, profile.id):
            reconcile_profile_skills(db, profile.id)
            seed_subskills_for_profile(db, profile.id)
        return profile

    profile = Profile(is_default=True, data=json.dumps(DEFAULT_PROFILE_DATA, ensure_ascii=False))
    db.add(profile)
    db.flush()
    _seed_skills(db, profile)
    _ensure_preferred_skills(db, profile)
    reconcile_profile_skills(db, profile.id)
    seed_subskills_for_profile(db, profile.id)
    db.commit()
    db.refresh(profile)
    return profile


def _seed_skills(db: Session, profile: Profile) -> None:
    for idx, block in enumerate(DEFAULT_COMPETENCES):
        cat = get_or_create_category(
            db,
            profile_id=profile.id,
            name=block["label"],
            source="seed",
            sort_order=idx,
        )
        for name, level in block["items"]:
            upsert_skill(
                db,
                profile_id=profile.id,
                category=cat,
                name=name,
                level=level,
                source="profile",
            )
    db.commit()


def _ensure_preferred_skills(db: Session, profile: Profile) -> None:
    """Ajoute les technos préférées manquantes sur un profil existant."""
    existing = {
        s.name_normalized
        for s in db.query(Skill).filter(Skill.profile_id == profile.id).all()
    }
    from app.services.sanitize import normalize_name

    cat_by_label = {
        c.name: c
        for c in db.query(Category).filter(Category.profile_id == profile.id).all()
    }
    for block in DEFAULT_COMPETENCES:
        cat = cat_by_label.get(block["label"])
        if not cat:
            cat = get_or_create_category(
                db,
                profile_id=profile.id,
                name=block["label"],
                source="seed",
            )
        for name, level in block["items"]:
            if normalize_name(name) not in existing:
                upsert_skill(
                    db,
                    profile_id=profile.id,
                    category=cat,
                    name=name,
                    level=level,
                    source="profile",
                )
                existing.add(normalize_name(name))
    db.commit()


def profile_data(profile: Profile) -> dict:
    return json.loads(profile.data)


def skills_snapshot(db: Session, profile: Profile) -> list[dict]:
    cats = (
        db.query(Category)
        .filter(Category.profile_id == profile.id)
        .order_by(Category.sort_order, Category.name)
        .all()
    )
    subs_map = subskills_by_skill_id(db, profile.id)
    out: list[dict] = []
    for cat in cats:
        skills = (
            db.query(Skill)
            .filter(Skill.category_id == cat.id)
            .order_by(nulls_last(Skill.level.desc()), Skill.name)
            .all()
        )
        out.append(
            {
                "category": cat.name,
                "skills": [
                    {
                        "name": s.name,
                        "level": s.level,
                        "source": s.source,
                        "preferred": s.name_normalized in PREFERRED_TECH_NORMALIZED,
                        "subskills": [
                            {
                                "name": sub.name,
                                "level": sub.level,
                                "source": sub.source,
                            }
                            for sub in subs_map.get(s.id, [])
                        ],
                    }
                    for s in skills
                ],
            }
        )
    return out


def persist_job_skills(
    db: Session,
    profile: Profile,
    categories: list[dict],
) -> None:
    """Persiste skills offre (level=None) fusionnées par catégorie."""
    from app.services.sanitize import normalize_name
    from app.services.subskills import upsert_subskill

    existing_norms = {
        s.name_normalized
        for s in db.query(Skill).filter(Skill.profile_id == profile.id).all()
    }
    sub_norms = {
        s.name_normalized
        for s in db.query(Subskill).filter(Subskill.profile_id == profile.id).all()
    }
    skills_by_norm = {
        s.name_normalized: s
        for s in db.query(Skill).filter(Skill.profile_id == profile.id).all()
    }

    for block in categories:
        cat_name = str(block.get("name", "")).strip()
        if not cat_name:
            continue
        cat = get_or_create_category(
            db,
            profile_id=profile.id,
            name=cat_name,
            source="job",
        )
        for raw in block.get("skills", []):
            name = str(raw).strip()
            if not name:
                continue
            norm = normalize_name(name)
            if norm in existing_norms or norm in sub_norms:
                continue

            # Tenter rattachement subskill si match connu sous un parent préféré
            parent_skill = _find_parent_for_job_skill(name, skills_by_norm)
            if parent_skill:
                upsert_subskill(
                    db,
                    profile_id=profile.id,
                    skill=parent_skill,
                    name=name,
                    level=None,
                    source="job",
                )
                sub_norms.add(norm)
                continue

            skill = upsert_skill(
                db,
                profile_id=profile.id,
                category=cat,
                name=name,
                level=None,
                source="job",
            )
            if skill:
                existing_norms.add(skill.name_normalized)
    db.commit()


def _find_parent_for_job_skill(name: str, skills_by_norm: dict) -> Skill | None:
    from app.seed import DEFAULT_SUBSKILLS
    from app.services.sanitize import normalize_name

    norm = normalize_name(name)
    for parent_name, items in DEFAULT_SUBSKILLS.items():
        for sub_name, _ in items:
            if normalize_name(sub_name) == norm:
                parent = skills_by_norm.get(normalize_name(parent_name))
                if parent:
                    return parent
    return None
