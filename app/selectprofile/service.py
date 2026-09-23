from __future__ import annotations

from app import db as store


def _norm_lang(lang: str) -> str:
    return "en" if lang == "en" else "fr"


def list_profiles() -> list[dict]:
    return store.list_profile_summaries()


def get_profile_detail(profile_id: str, lang: str) -> dict:
    lang = _norm_lang(lang)
    profile = store.get_profile(profile_id)
    if not profile:
        raise KeyError("Profil introuvable")
    markdown = ""
    stored = profile.get("markdown") or {}
    if isinstance(stored, dict):
        markdown = str(stored.get(lang) or "").strip()
    return {
        "id": profile["id"],
        "lang": lang,
        "title": (profile.get("profile") or {}).get(lang)
        or (profile.get("profile") or {}).get("fr")
        or "",
        "profile": profile.get("profile", {}),
        "markdown": markdown,
    }
