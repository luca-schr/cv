"""Subskills : compétences spécifiques rattachées à une skill parente."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models import Skill, Subskill
from app.seed import DEFAULT_SUBSKILLS, PREFERRED_TECH_NORMALIZED, TITLE_TECH_ALIASES
from app.services.sanitize import normalize_name


def upsert_subskill(
    db: Session,
    *,
    profile_id: int,
    skill: Skill,
    name: str,
    level: int | None = None,
    source: str = "profile",
) -> Subskill | None:
    norm = normalize_name(name)
    if not norm:
        return None
    existing = (
        db.query(Subskill)
        .filter(Subskill.profile_id == profile_id, Subskill.name_normalized == norm)
        .first()
    )
    if existing:
        if existing.skill_id != skill.id:
            existing.skill_id = skill.id
        if existing.level is None and level is not None:
            existing.level = level
        return existing
    sub = Subskill(
        profile_id=profile_id,
        skill_id=skill.id,
        name=name.strip(),
        name_normalized=norm,
        level=level,
        source=source,
    )
    db.add(sub)
    db.flush()
    return sub


def seed_subskills_for_profile(db: Session, profile_id: int) -> int:
    """Insère les subskills par défaut. Retourne le nombre créé."""
    skills_by_norm = {
        s.name_normalized: s
        for s in db.query(Skill).filter(Skill.profile_id == profile_id).all()
    }
    created = 0
    for parent_name, items in DEFAULT_SUBSKILLS.items():
        parent = skills_by_norm.get(normalize_name(parent_name))
        if not parent:
            continue
        for name, level in items:
            before = (
                db.query(Subskill)
                .filter(
                    Subskill.profile_id == profile_id,
                    Subskill.name_normalized == normalize_name(name),
                )
                .count()
            )
            upsert_subskill(
                db,
                profile_id=profile_id,
                skill=parent,
                name=name,
                level=level,
                source="profile",
            )
            after = (
                db.query(Subskill)
                .filter(
                    Subskill.profile_id == profile_id,
                    Subskill.name_normalized == normalize_name(name),
                )
                .count()
            )
            if after > before:
                created += 1
    db.commit()
    return created


def reconcile_profile_skills(db: Session, profile_id: int) -> None:
    """Déplace les skills devenues subskills (ex. TanStack Query → React)."""
    skills = db.query(Skill).filter(Skill.profile_id == profile_id).all()
    skills_by_norm = {s.name_normalized: s for s in skills}

    for parent_name, items in DEFAULT_SUBSKILLS.items():
        parent = skills_by_norm.get(normalize_name(parent_name))
        if not parent:
            continue
        for sub_name, level in items:
            sub_norm = normalize_name(sub_name)
            orphan = skills_by_norm.get(sub_norm)
            if orphan and orphan.id != parent.id:
                upsert_subskill(
                    db,
                    profile_id=profile_id,
                    skill=parent,
                    name=sub_name,
                    level=level or orphan.level,
                    source=orphan.source,
                )
                db.delete(orphan)
                del skills_by_norm[sub_norm]
    db.commit()


def subskills_by_skill_id(db: Session, profile_id: int) -> dict[int, list[Subskill]]:
    rows = (
        db.query(Subskill)
        .filter(Subskill.profile_id == profile_id)
        .order_by(Subskill.name)
        .all()
    )
    out: dict[int, list[Subskill]] = {}
    for row in rows:
        out.setdefault(row.skill_id, []).append(row)
    return out


def is_preferred_skill(skill_name: str) -> bool:
    return normalize_name(skill_name) in PREFERRED_TECH_NORMALIZED


def extract_title_technologies(job_title: str, skills_snapshot: list[dict]) -> list[str]:
    """Détecte les technos citées dans l'intitulé du poste."""
    if not job_title:
        return []
    known: dict[str, str] = {}
    for block in skills_snapshot:
        for skill in block.get("skills", []):
            name = skill.get("name", "")
            if name:
                known[normalize_name(name)] = name

    found: list[str] = []
    title_lower = job_title.lower()
    for pattern, label in TITLE_TECH_ALIASES:
        if not re.search(pattern, title_lower, re.IGNORECASE):
            continue
        norm = normalize_name(label)
        resolved = known.get(norm)
        if not resolved:
            for knorm, kname in known.items():
                if norm in knorm or knorm in norm:
                    resolved = kname
                    break
        found.append(resolved or label)

    return list(dict.fromkeys(found))


def collect_job_terms(job_analysis, job_text: str, *, skills_snapshot: list[dict] | None = None) -> set[str]:
    terms: set[str] = set()
    for block in job_analysis.categories or []:
        name = str(block.get("name", "")).strip()
        if name:
            terms.add(normalize_name(name))
        for raw in block.get("skills", []):
            s = str(raw).strip()
            if s:
                terms.add(normalize_name(s))
    if getattr(job_analysis, "job_title", None) and skills_snapshot:
        for tech in extract_title_technologies(job_analysis.job_title, skills_snapshot):
            terms.add(normalize_name(tech))
    for token in job_text.lower().replace("/", " ").replace(".", " ").split():
        cleaned = normalize_name(token)
        if len(cleaned) >= 3:
            terms.add(cleaned)
    return terms


def _term_matches(sub_norm: str, job_terms: set[str]) -> bool:
    if sub_norm in job_terms:
        return True
    return any(sub_norm in t or t in sub_norm for t in job_terms if len(t) >= 4)


def select_relevant_subskills(
    skills_snapshot: list[dict],
    *,
    job_analysis,
    job_text: str,
) -> list[dict]:
    """
    Sélectionne les subskills à mettre en avant selon l'offre et les technos préférées.
    Retourne [{parent, parent_level, name, level, reason}, ...]
    """
    job_terms = collect_job_terms(job_analysis, job_text, skills_snapshot=skills_snapshot)
    selected: list[dict] = []
    seen: set[str] = set()

    for block in skills_snapshot:
        for skill in block.get("skills", []):
            parent = skill.get("name", "")
            parent_norm = normalize_name(parent)
            parent_level = skill.get("level")
            parent_preferred = parent_norm in PREFERRED_TECH_NORMALIZED
            parent_in_job = _term_matches(parent_norm, job_terms)

            for sub in skill.get("subskills", []):
                sub_name = sub.get("name", "")
                sub_norm = normalize_name(sub_name)
                if not sub_norm or sub_norm in seen:
                    continue

                sub_in_job = _term_matches(sub_norm, job_terms)
                sub_level = sub.get("level")
                strong_sub = sub_level is not None and sub_level >= 4

                reason = None
                if sub_in_job:
                    reason = "offre"
                elif parent_in_job and (strong_sub or parent_preferred):
                    reason = "parent_offre"
                elif parent_preferred and strong_sub:
                    reason = "predilection"
                elif parent_preferred and parent_level is not None and parent_level >= 4:
                    reason = "stack_preferee"

                if reason:
                    seen.add(sub_norm)
                    selected.append(
                        {
                            "parent": parent,
                            "parent_level": parent_level,
                            "name": sub_name,
                            "level": sub_level,
                            "reason": reason,
                        }
                    )

    # Priorité : offre > parent_offre > predilection > stack_preferee
    priority = {"offre": 0, "parent_offre": 1, "predilection": 2, "stack_preferee": 3}
    selected.sort(key=lambda s: (priority.get(s["reason"], 9), -(s["level"] or 0)))
    return selected[:18]


def _format_skill_item(parent: str, subs: list[str]) -> str:
    if subs:
        return f"{parent} — {', '.join(subs)}"
    return parent


def build_skill_groups_for_cv(
    skills_snapshot: list[dict],
    *,
    relevant_subskills: list[dict],
    title_technologies: list[str],
    job_analysis,
    job_text: str,
) -> list[dict]:
    """Construit les groupes compétences avec skills + subskills visibles."""
    job_terms = collect_job_terms(job_analysis, job_text, skills_snapshot=skills_snapshot)
    title_norms = {normalize_name(t) for t in title_technologies}

    parent_subs: dict[str, list[str]] = {}
    for item in relevant_subskills:
        parent_subs.setdefault(item["parent"], [])
        if item["name"] not in parent_subs[item["parent"]]:
            parent_subs[item["parent"]].append(item["name"])

    groups_by_cat: dict[str, list[str]] = {}
    for block in skills_snapshot:
        cat = block.get("category", "Compétences")
        for skill in block.get("skills", []):
            name = skill.get("name", "")
            if not name:
                continue
            norm = normalize_name(name)
            in_title = norm in title_norms or any(
                norm in normalize_name(t) or normalize_name(t) in norm for t in title_technologies
            )
            in_job = _term_matches(norm, job_terms)
            preferred = skill.get("preferred") or norm in PREFERRED_TECH_NORMALIZED
            level = skill.get("level") or 0
            subs = parent_subs.get(name, [])

            if in_title:
                if not subs:
                    subs = [s["name"] for s in skill.get("subskills", [])[:4]]
            elif not (in_job and (preferred or level >= 3)) and not subs:
                continue

            item = _format_skill_item(name, subs[:4])
            if item not in groups_by_cat.get(cat, []):
                groups_by_cat.setdefault(cat, []).append(item)

    return [{"label": cat, "items": items} for cat, items in groups_by_cat.items() if items]


def merge_skill_groups(llm_groups: list[dict], built_groups: list[dict]) -> list[dict]:
    """Fusionne groupes LLM + groupes construits (titre/subskills garantis)."""
    if not built_groups:
        return llm_groups
    if not llm_groups:
        return built_groups

    merged: dict[str, list[str]] = {}
    for g in llm_groups:
        label = g.get("label", "").strip()
        if label:
            merged[label] = list(g.get("items", []))

    for g in built_groups:
        label = g.get("label", "").strip()
        if not label:
            continue
        existing = merged.setdefault(label, [])
        existing_norms = {normalize_name(i) for i in existing}
        for item in g.get("items", []):
            item_norm = normalize_name(item.split("—")[0].split("(")[0])
            if not any(item_norm in n or n in item_norm for n in existing_norms):
                existing.append(item)

    return [{"label": k, "items": v} for k, v in merged.items() if v]


def format_subskill_hints(selected: list[dict]) -> list[str]:
    """Format compact pour le prompt LLM."""
    lines: list[str] = []
    for item in selected:
        lvl = f" (n.{item['level']})" if item.get("level") else ""
        lines.append(f"- {item['parent']} -> {item['name']}{lvl} [{item['reason']}]")
    return lines


def enrich_skill_groups(
    skill_groups: list[dict],
    selected: list[dict],
    *,
    max_inject: int = 10,
) -> list[dict]:
    """
    Post-traitement : injecte les subskills dans skill_groups si le LLM les a omises.
    Format item : « Parent (Sub1, Sub2) » ou « Sub » si parent déjà présent.
    """
    if not selected:
        return skill_groups

    injected = 0
    parent_to_subs: dict[str, list[str]] = {}
    for item in selected:
        parent_to_subs.setdefault(item["parent"], []).append(item["name"])

    groups = [dict(g) for g in skill_groups]
    all_items_norm = {
        normalize_name(i)
        for g in groups
        for i in g.get("items", [])
    }

    for parent, subs in parent_to_subs.items():
        if injected >= max_inject:
            break
        parent_norm = normalize_name(parent)
        parent_found = any(
            parent_norm in normalize_name(i) or normalize_name(i) in parent_norm
            for i in all_items_norm
        )

        missing_subs = [
            s for s in subs if normalize_name(s) not in all_items_norm and injected < max_inject
        ]
        if not missing_subs:
            continue

        if parent_found:
            for g in groups:
                new_items = []
                for item in g.get("items", []):
                    item_norm = normalize_name(item.split("—")[0].split("(")[0])
                    if parent_norm in item_norm or item_norm in parent_norm:
                        add = [s for s in missing_subs if s not in item]
                        if add:
                            suffix = ", ".join(add)
                            if "—" in item:
                                new_items.append(f"{item}, {suffix}")
                            else:
                                new_items.append(f"{item} — {suffix}")
                            injected += len(add)
                        else:
                            new_items.append(item)
                    else:
                        new_items.append(item)
                g["items"] = new_items
        elif groups:
            groups[0]["items"] = list(groups[0].get("items", [])) + [
                _format_skill_item(parent, missing_subs)
            ]
            injected += len(missing_subs)
            all_items_norm.update(normalize_name(s) for s in missing_subs)

    return groups
