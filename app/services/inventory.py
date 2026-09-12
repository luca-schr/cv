"""Inventaire lexical du CV source — ancrage anti-hallucination."""

from __future__ import annotations

import re
import unicodedata

from app.services.analyzer import load_analysis_config

_STOP = {
    "les", "des", "une", "un", "et", "ou", "de", "du", "la", "le", "en", "au", "aux",
    "pour", "par", "sur", "avec", "dans", "plus", "sans", "the", "and", "for", "with",
    "to", "of", "in", "a", "an", "site", "web", "projet", "projets", "equipe",
}


def fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return stripped.lower()


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9][a-z0-9.+#/-]{1,}", fold(text))
        if token not in _STOP and len(token) >= 2
    ]


def _item_text(item: object) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(item.get("text") or item.get("term") or "")
    return str(item or "")


def collect_phrases(cv_data: dict) -> list[str]:
    phrases: list[str] = []
    phrases.extend(cv_data.get("technos_root") or [])
    phrases.extend(cv_data.get("technos_extended") or [])
    profil = cv_data.get("profil") or {}
    if profil.get("text"):
        phrases.append(str(profil["text"]))
    phrases.extend(profil.get("services") or [])
    for cat in cv_data.get("competences") or []:
        if cat.get("label"):
            phrases.append(str(cat["label"]))
        for item in cat.get("items") or []:
            phrases.append(_item_text(item))
    for exp in cv_data.get("experiences") or []:
        phrases.append(f"{exp.get('title', '')} {exp.get('company', '')}")
        for bullet in exp.get("bullets") or []:
            phrases.append(_item_text(bullet))
    for formation in cv_data.get("formations") or []:
        phrases.append(f"{formation.get('title', '')} {formation.get('school', '')}")
        for bullet in formation.get("bullets") or []:
            phrases.append(_item_text(bullet))
        if formation.get("description"):
            phrases.append(str(formation["description"]))
    if cv_data.get("certifications"):
        phrases.append(str(cv_data["certifications"]))
    return [p.strip() for p in phrases if str(p).strip()]


def collect_blob(cv_data: dict) -> str:
    return " ".join(collect_phrases(cv_data))


def alias_groups() -> dict[str, list[str]]:
    config = load_analysis_config()
    groups: dict[str, list[str]] = {}
    for tag, aliases in (config.get("tag_aliases") or {}).items():
        groups[str(tag)] = [fold(str(alias)) for alias in aliases]
    return groups


def term_in_inventory(term: str, blob: str, groups: dict[str, list[str]]) -> str | None:
    """Retourne le tag/terme matché si présent dans le blob CV."""
    folded_blob = fold(blob)
    folded_term = fold(term).strip()
    if len(folded_term) < 2:
        return None
    for tag, aliases in groups.items():
        variants = [fold(tag), *aliases]
        if folded_term in variants or any(folded_term == alias or alias == folded_term for alias in variants):
            if any(alias and alias in folded_blob for alias in variants if len(alias) >= 2):
                return tag
        if any(alias and (alias in folded_term or folded_term in alias) for alias in variants if len(alias) >= 3):
            if any(alias and alias in folded_blob for alias in variants if len(alias) >= 2):
                return tag
    if folded_term in folded_blob:
        return term
    tokens = tokenize(term)
    if tokens and all(token in folded_blob for token in tokens if len(token) >= 3):
        return term
    return None


def phrase_is_grounded(phrase: str, blob: str) -> bool:
    tokens = [t for t in tokenize(phrase) if len(t) >= 3]
    if not tokens:
        return True
    folded_blob = fold(blob)
    hits = sum(1 for token in tokens if token in folded_blob)
    return hits >= max(1, (len(tokens) + 2) // 3)
