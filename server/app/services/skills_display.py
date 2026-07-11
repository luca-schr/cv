"""Filtre dynamique des catégories skills pour le CV (~80 % couverture)."""

from __future__ import annotations

COVERAGE_TARGET = 0.8


def filter_categories_for_cv(
    skill_groups: list[dict],
    *,
    coverage: float = COVERAGE_TARGET,
) -> list[dict]:
    """
    skill_groups: [{ "label": str, "items": [str, ...] }, ...]
    Garde les catégories les plus fournies jusqu'à couvrir >= coverage des skills.
    """
    groups = [
        {"label": g.get("label", "").strip(), "items": [str(i).strip() for i in g.get("items", []) if str(i).strip()]}
        for g in skill_groups
        if g.get("label") and g.get("items")
    ]
    if not groups:
        return []

    ranked = sorted(groups, key=lambda g: len(g["items"]), reverse=True)
    total = sum(len(g["items"]) for g in ranked)
    if total == 0:
        return []

    threshold = max(1, int(total * coverage + 0.999))
    kept: list[dict] = []
    count = 0
    for group in ranked:
        kept.append(group)
        count += len(group["items"])
        if count >= threshold:
            break
    return kept


def build_skill_groups_from_db(categories: list, skills_by_cat: dict[int, list]) -> list[dict]:
    groups: list[dict] = []
    for cat in categories:
        skills = skills_by_cat.get(cat.id, [])
        if not skills:
            continue
        items = [s.name for s in skills]
        groups.append({"label": cat.name, "items": items})
    return groups
