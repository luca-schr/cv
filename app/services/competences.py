"""Normalisation des compétences vers les 5 catégories fixes."""

from __future__ import annotations

SKILL_CATEGORIES = [
    "Front-end",
    "Back-end",
    "Data & CMS",
    "DevOps",
    "Cybersécurité",
]

_CATEGORY_ALIASES: dict[str, str] = {
    "front-end": "Front-end",
    "frontend": "Front-end",
    "front end": "Front-end",
    "react & interfaces": "Front-end",
    "vue.js & intégration": "Front-end",
    "vue.js & integration": "Front-end",
    "back-end": "Back-end",
    "backend": "Back-end",
    "back end": "Back-end",
    "node.js & back-end": "Back-end",
    "node.js & backend": "Back-end",
    "data & cms": "Data & CMS",
    "données & cms": "Data & CMS",
    "donnees & cms": "Data & CMS",
    "devops": "DevOps",
    "devops & livraison": "DevOps",
    "cybersécurité": "Cybersécurité",
    "cybersecurite": "Cybersécurité",
    "sécurité": "Cybersécurité",
    "securite": "Cybersécurité",
    "produit & méthodes": "Produit & méthodes",
    "produit et methodes": "Produit & méthodes",
    "produit & methodes": "Produit & méthodes",
    "ux / ui": "UX / UI",
    "ux/ui": "UX / UI",
    "ux ui": "UX / UI",
    "seo & acquisition": "SEO & acquisition",
    "seo et acquisition": "SEO & acquisition",
    "cms & no-code": "CMS & no-code",
    "cms et no-code": "CMS & no-code",
    "développement": "Développement",
    "developpement": "Développement",
}


def _item_terms(items: list) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        term = (item if isinstance(item, str) else item.get("term", "")).strip()
        key = term.lower()
        if term and key not in seen:
            seen.add(key)
            out.append(term)
    return out


def _resolve_label(label: str) -> str | None:
    key = label.strip().lower()
    if key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[key]
    for canonical in SKILL_CATEGORIES:
        if canonical.lower() == key:
            return canonical
    return None


def normalize_competences(
    competences: list[dict] | None,
    *,
    english: bool = False,
) -> list[dict]:
    _ = english
    ordered: list[dict] = []
    index_by_label: dict[str, int] = {}

    for cat in competences or []:
        label = str(cat.get("label", "")).strip()
        terms = _item_terms(cat.get("items", []))
        if not label or not terms:
            continue
        canonical = _resolve_label(label) or label
        key = canonical.lower()
        if key in index_by_label:
            existing = ordered[index_by_label[key]]
            existing["items"] = _item_terms(existing["items"] + terms)
            continue
        index_by_label[key] = len(ordered)
        ordered.append({"label": canonical, "items": terms})
    return ordered
