"""Nettoyage léger de texte (titres d'offre)."""

from __future__ import annotations

import re

_TITLE_PARASITES = (
    r"\s*[\(\[]?\s*H\s*/\s*F\s*[\)\]]?\s*$",
    r"\s*[\(\[]?\s*F\s*/\s*H\s*[\)\]]?\s*$",
    r"\s*[-–—/]\s*H\s*/\s*F\s*$",
    r"\s*[-–—/]\s*M\s*/\s*F\s*$",
    r"\s*[-–—]\s*$",
)


def sanitize_cv_title(title: str) -> str:
    """Retire les suffixes parasites des intitulés d'offre (ex. « - H/F »)."""
    cleaned = title.strip()
    if not cleaned:
        return cleaned
    for pattern in _TITLE_PARASITES:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", cleaned).strip()
