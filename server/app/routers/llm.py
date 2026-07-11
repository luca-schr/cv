from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.bootstrap import seed_profile_if_needed
from app.database import get_db
from app.models import Category, Skill
from app.schemas import CategoryOut, ProfileSkillsOut, SkillOut, SubskillOut
from app.services.llm import check_ollama_status
from app.services.subskills import subskills_by_skill_id
from app.seed import PREFERRED_TECH_NORMALIZED

router = APIRouter(tags=["llm"])


@router.get("/llm/status")
def llm_status():
    return check_ollama_status()


@router.get("/profile/skills", response_model=ProfileSkillsOut)
def profile_skills(db: Session = Depends(get_db)):
    profile = seed_profile_if_needed(db)
    cats = (
        db.query(Category)
        .filter(Category.profile_id == profile.id)
        .order_by(Category.sort_order, Category.name)
        .all()
    )
    subs_map = subskills_by_skill_id(db, profile.id)
    categories: list[CategoryOut] = []
    for cat in cats:
        skills = (
            db.query(Skill)
            .filter(Skill.category_id == cat.id)
            .order_by(Skill.name)
            .all()
        )
        categories.append(
            CategoryOut(
                id=cat.id,
                name=cat.name,
                source=cat.source,
                skills=[
                    SkillOut(
                        id=s.id,
                        name=s.name,
                        level=s.level,
                        source=s.source,
                        preferred=s.name_normalized in PREFERRED_TECH_NORMALIZED,
                        subskills=[
                            SubskillOut(
                                id=sub.id,
                                name=sub.name,
                                level=sub.level,
                                source=sub.source,
                                parent_skill_id=sub.skill_id,
                            )
                            for sub in subs_map.get(s.id, [])
                        ],
                    )
                    for s in skills
                ],
            )
        )
    return ProfileSkillsOut(categories=categories)
