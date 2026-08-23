"""Matching offre ↔ profil : keywords + shortlist pour Ollama."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from app.services.ollama import chat_json

STOP = frozenset(
    {
        "de",
        "du",
        "des",
        "le",
        "la",
        "les",
        "et",
        "en",
        "un",
        "une",
        "the",
        "and",
        "or",
        "for",
        "with",
    }
)

MATCH_THRESHOLD = 6
LOW_SCORE_SKIP_OLLAMA = 3
SHORTLIST_SIZE = 5
NEED_BETTER_CV_MSG = "Besoin de créer un CV plus pertinent"
SKILL_GAP_RATIO = 0.55
SKILL_GAP_MIN_JOB_SKILLS = 3


def _strip_accents(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _normalize(text: str | None) -> str:
    s = _strip_accents(str(text or "").lower())
    s = re.sub(r"[^a-z0-9+.#/\s-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokenize(text: str | None) -> list[str]:
    return [
        t
        for t in (tok.strip() for tok in re.split(r"[\s,/|;]+", _normalize(text)))
        if len(t) >= 2 and t not in STOP
    ]


def _escape_re(s: str) -> str:
    return re.escape(s)


def score_profile(job_text: str, profile: dict[str, Any]) -> dict[str, Any]:
    blob = _normalize(job_text)
    if not blob or len(blob) < 10:
        return {"score": 0, "hits": []}

    keywords = [k.strip() for k in str(profile.get("keywords") or "").split(",") if k.strip()]
    name_tokens = _tokenize(f"{profile.get('name', '')} {profile.get('title') or ''}")
    pool = list(dict.fromkeys([*keywords, *name_tokens]))

    score = 0
    hits: list[str] = []

    for raw in pool:
        k = _normalize(raw)
        if not k or len(k) < 2:
            continue
        escaped = _escape_re(k)
        pattern = re.compile(rf"(?:^|[^a-z0-9]){escaped}(?:[^a-z0-9]|$)", re.IGNORECASE)
        if pattern.search(blob) or k in blob:
            weight = 3 if len(k) >= 4 else 2
            score += weight
            hits.append(raw)

    title = _normalize(profile.get("title") or profile.get("name") or "")
    if title and title[: min(len(title), 24)] in blob:
        score += 4

    return {"score": score, "hits": list(dict.fromkeys(hits))[:12]}


def extract_job_skill_hints(job_text: str) -> list[str]:
    """Compétences « techniques » citées dans l'offre (heuristique légère)."""
    blob = _normalize(job_text)
    hints: set[str] = set()
    pattern = re.compile(
        r"(?:^|[^a-z0-9])([a-z][a-z0-9+#.]{1,24}|c#|\.net|node\.?js|next\.?js|vue\.?js)(?=[^a-z0-9]|$)",
        re.IGNORECASE,
    )
    for m in pattern.finditer(blob):
        t = _normalize(m.group(1))
        if len(t) >= 2 and t not in STOP and not re.match(r"^\d+$", t):
            hints.add(t)
    return list(hints)


def assess_skill_gap(job_text: str, profile: dict[str, Any] | None) -> dict[str, Any]:
    """Écart compétences offre ↔ profil (keywords + nom)."""
    job_skills = extract_job_skill_hints(job_text)
    profile_pool = [
        *[_normalize(k.strip()) for k in str((profile or {}).get("keywords") or "").split(",") if k.strip()],
        *_tokenize(
            f"{(profile or {}).get('name') or ''} "
            f"{(profile or {}).get('title') or ''} "
            f"{(profile or {}).get('summary') or ''}"
        ),
    ]
    profile_set = set(profile_pool)

    missing: list[str] = []
    covered = 0
    for js in job_skills:
        hit = js in profile_set or any(
            len(p) >= 3 and len(js) >= 3 and (js in p or p in js) for p in profile_set
        )
        if hit:
            covered += 1
        else:
            missing.append(js)

    total = len(job_skills)
    ratio = (len(missing) / total) if total > 0 else 0.0
    gap = total >= SKILL_GAP_MIN_JOB_SKILLS and ratio >= SKILL_GAP_RATIO

    return {
        "gap": gap,
        "missing": missing[:10],
        "jobSkills": job_skills[:16],
        "covered": covered,
        "ratio": ratio,
    }


def _with_gap_fields(
    result: dict[str, Any],
    job_text: str,
    profile: dict[str, Any] | None,
) -> dict[str, Any]:
    if profile:
        skill_gap = assess_skill_gap(job_text, profile)
    else:
        skill_gap = {
            "gap": True,
            "missing": [],
            "jobSkills": extract_job_skill_hints(job_text),
            "covered": 0,
            "ratio": 1,
        }

    score = result.get("score")
    needs_better = (
        not result.get("matched")
        or skill_gap["gap"]
        or (score is not None and score < MATCH_THRESHOLD)
    )

    message = result.get("message")
    if needs_better and not result.get("matched"):
        message = NEED_BETTER_CV_MSG
    elif needs_better and result.get("matched"):
        message = f"{result.get('message')} — {NEED_BETTER_CV_MSG}"

    return {
        **result,
        "needs_better_cv": needs_better,
        "missing_skills": skill_gap["missing"],
        "skill_gap_ratio": skill_gap["ratio"],
        "message": message,
    }


def rank_profiles(job_text: str, profiles: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Classe tous les profils par score décroissant."""
    ranked = []
    for profile in profiles or []:
        scored = score_profile(job_text, profile)
        ranked.append({"profile": profile, "score": scored["score"], "hits": scored["hits"]})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked


def find_best_profile(job_text: str, profiles: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Matching keywords seul (fallback)."""
    ranked = rank_profiles(job_text, profiles)
    best = ranked[0] if ranked else None
    if not best or best["score"] < MATCH_THRESHOLD:
        return _with_gap_fields(
            {
                "matched": False,
                "message": NEED_BETTER_CV_MSG,
                "score": best["score"] if best else 0,
                "hits": best["hits"] if best else [],
                "profile": None,
                "shortlist": [],
            },
            job_text,
            best["profile"] if best else None,
        )
    return _with_gap_fields(
        {
            "matched": True,
            "message": f"Profil proposé : {best['profile']['name']}",
            "score": best["score"],
            "hits": best["hits"],
            "profile": best["profile"],
            "shortlist": ranked[:SHORTLIST_SIZE],
        },
        job_text,
        best["profile"],
    )


def build_match_context(job_text: str, profiles: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Prépare shortlist pour Ollama. shortlist vide + skipOllama = skip Ollama."""
    ranked = rank_profiles(job_text, profiles)
    best = ranked[0] if ranked else None
    if not best or best["score"] < LOW_SCORE_SKIP_OLLAMA:
        return _with_gap_fields(
            {
                "skipOllama": True,
                "matched": False,
                "message": NEED_BETTER_CV_MSG,
                "score": best["score"] if best else 0,
                "hits": best["hits"] if best else [],
                "profile": None,
                "shortlist": [],
            },
            job_text,
            best["profile"] if best else None,
        )

    shortlist = [
        {
            "id": r["profile"].get("id"),
            "name": r["profile"].get("name"),
            "category": r["profile"].get("category_name")
            or r["profile"].get("category_label")
            or "",
            "title": r["profile"].get("title"),
            "summary": r["profile"].get("summary"),
            "keywords": r["profile"].get("keywords"),
            "score": r["score"],
            "hits": r["hits"],
            "profile": r["profile"],
        }
        for r in ranked
        if r["score"] > 0
    ][:SHORTLIST_SIZE]

    if not shortlist:
        return _with_gap_fields(
            {
                "skipOllama": True,
                "matched": False,
                "message": NEED_BETTER_CV_MSG,
                "score": best["score"],
                "hits": best["hits"],
                "profile": None,
                "shortlist": [],
            },
            job_text,
            best["profile"],
        )

    return {
        "skipOllama": False,
        "bestKeywords": best,
        "shortlist": shortlist,
        "ranked": ranked,
    }


def resolve_ollama_decision(
    decision: dict[str, Any] | None,
    context: dict[str, Any],
    job_text: str = "",
) -> dict[str, Any]:
    """Résout la décision Ollama contre la shortlist + fallback keywords."""
    shortlist = context.get("shortlist") or []
    ids = {int(s["id"]) for s in shortlist if s.get("id") is not None}
    best = context.get("bestKeywords")
    reason = str((decision or {}).get("reason") or "").strip()[:220]

    profile_id = (decision or {}).get("profile_id")
    if profile_id in ("null", ""):
        profile_id = None
    if profile_id is not None:
        try:
            profile_id = int(profile_id)
        except (TypeError, ValueError):
            profile_id = None

    try:
        confidence = float((decision or {}).get("confidence"))
        low_confidence = confidence < 0.45
    except (TypeError, ValueError):
        confidence = float("nan")
        low_confidence = False

    if profile_id is not None and profile_id in ids and not low_confidence:
        hit = next(s for s in shortlist if int(s["id"]) == profile_id)
        return _with_gap_fields(
            {
                "matched": True,
                "message": f"Profil proposé : {hit['name']}",
                "score": hit["score"],
                "hits": hit["hits"],
                "profile": hit["profile"],
                "reason": reason,
                "source": "ollama",
                "fallback": False,
            },
            job_text,
            hit["profile"],
        )

    if best and best["score"] >= MATCH_THRESHOLD and not low_confidence and profile_id is not None:
        return _with_gap_fields(
            {
                "matched": True,
                "message": f"Profil proposé : {best['profile']['name']}",
                "score": best["score"],
                "hits": best["hits"],
                "profile": best["profile"],
                "reason": reason or "Fallback matching local (réponse Ollama invalide).",
                "source": "keywords",
                "fallback": True,
            },
            job_text,
            best["profile"],
        )

    if best and best["score"] >= MATCH_THRESHOLD and (profile_id is None or low_confidence):
        return _with_gap_fields(
            {
                "matched": True,
                "message": f"Profil proposé : {best['profile']['name']}",
                "score": best["score"],
                "hits": best["hits"],
                "profile": best["profile"],
                "reason": reason or NEED_BETTER_CV_MSG,
                "source": "ollama" if profile_id is None else "keywords",
                "fallback": profile_id is None,
            },
            job_text,
            best["profile"],
        )

    return _with_gap_fields(
        {
            "matched": False,
            "message": NEED_BETTER_CV_MSG,
            "score": best["score"] if best else 0,
            "hits": best["hits"] if best else [],
            "profile": None,
            "reason": reason or None,
            "source": "ollama",
            "fallback": False,
        },
        job_text,
        best["profile"] if best else None,
    )


async def match_with_ollama(
    job_text: str,
    shortlist: list[dict[str, Any]],
    *,
    english: bool = False,
) -> dict[str, Any]:
    """Demande à Ollama de choisir un profil dans la shortlist."""
    ids = [s.get("id") for s in shortlist if s.get("id") is not None]
    system = """Tu choisis le CV le plus pertinent pour cette offre.
Réponds en JSON strict :
{"profile_id": <id de la liste ou null>, "confidence": <nombre 0 à 1>, "reason": "<1 phrase>"}

Règles :
- profile_id DOIT être un id de la liste, ou null si aucun n'est crédible.
- Ne mélange pas les métiers : un poste chef de projet / PO n'est pas un CV développeur, et inversement, sauf offre clairement hybride.
- confidence < 0.45 si le fit est faible.
- reason en français, sauf si output_language est English.
"""
    user = {
        "output_language": "English" if english else "French",
        "job_text": str(job_text or "")[:6000],
        "profiles": [
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "title": s.get("title"),
                "category": s.get("category"),
                "summary": s.get("summary"),
                "keywords": s.get("keywords"),
                "keyword_score": s.get("score"),
                "hits": s.get("hits"),
            }
            for s in shortlist
        ],
        "valid_ids": ids,
    }
    raw = await chat_json(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        temperature=0.1,
        timeout_seconds=45,
    )
    if not isinstance(raw, dict):
        return {}
    return raw
