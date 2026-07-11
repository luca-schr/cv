"""Normalisation noms (catégories, skills)."""

from __future__ import annotations

import re
import unicodedata


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFD", value.strip().lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("œ", "oe").replace("æ", "ae")
    text = re.sub(r"[^a-z0-9+#./\s-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace(" ", "-")


def sanitize_cv_title(title: str) -> str:
    cleaned = re.sub(r"\s{2,}", " ", title.strip())
    cleaned = re.sub(r"\bH\s*/\s*F\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*[-–—|]\s*$", "", cleaned)
    return cleaned.strip()[:90]
