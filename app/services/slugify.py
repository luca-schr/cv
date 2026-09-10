"""Slugs ASCII-safe pour noms de fichiers."""

from __future__ import annotations

import re
import unicodedata

_EXTRA_TRANSLATIONS = str.maketrans(
    {
        "œ": "oe",
        "Œ": "oe",
        "æ": "ae",
        "Æ": "ae",
        "ß": "ss",
    }
)


def slugify(text: str, *, max_len: int = 40) -> str:
    """Retire accents et caractères spéciaux ; conserve a-z, 0-9 et tirets."""
    raw = (text or "").strip()
    if not raw:
        return ""
    normalized = unicodedata.normalize("NFKD", raw)
    ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
    ascii_text = ascii_text.translate(_EXTRA_TRANSLATIONS).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        return ""
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    return slug


PROFILE_SLUGS = {
    "fullstack": {"fr": "developpeur-fullstack", "en": "fullstack-developer"},
    "chef-projet": {"fr": "chef-de-projet-digital", "en": "digital-project-manager"},
}

DEFAULT_COMPANY = {"fr": "defaut", "en": "default"}


def profile_file_slug(profile_key: str, *, english: bool = False) -> str:
    lang = "en" if english else "fr"
    mapped = PROFILE_SLUGS.get(profile_key or "", {}).get(lang)
    if mapped:
        return mapped
    return slugify(profile_key or "profil", max_len=40) or "profil"


def build_export_basename(
    *,
    profile_key: str = "fullstack",
    company: str | None = None,
    english: bool = False,
) -> str:
    """lucas-schrever-[profil]-[entreprise|defaut]-[fr|en]."""
    lang = "en" if english else "fr"
    company_slug = slugify(company or "", max_len=24)
    if not company_slug:
        company_slug = DEFAULT_COMPANY[lang]
    return f"lucas-schrever-{profile_file_slug(profile_key, english=english)}-{company_slug}-{lang}"


def build_cv_basename(role: str, company: str | None = None, *, role_max: int = 40, company_max: int = 18) -> str:
    """cv-[poste]-[entreprise] — entreprise omise si absente."""
    role_slug = slugify(role, max_len=role_max) or "master"
    role_slug = re.sub(r"^cv-+", "", role_slug).lstrip("-") or "master"
    company_slug = slugify(company or "", max_len=company_max)
    if company_slug and company_slug != "cv":
        return f"cv-{role_slug}-{company_slug}"
    return f"cv-{role_slug}"
