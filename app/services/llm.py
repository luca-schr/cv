"""Adaptation CV via l'API cloud Ollama (GLM-5.3-Flash)."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

import yaml

from app.config import settings
from app.llm_models import AdaptationPayload, JobBrief
from app.services.analyzer import JobAnalysis, _looks_like_job_title, load_analysis_config
from app.services.competences import SKILL_CATEGORIES
from app.services.inventory import collect_blob, collect_phrases, phrase_is_grounded
from app.services.matching import MatchReport, brief_from_heuristics
from app.services.sanitize import replace_long_dashes, sanitize_cv_title

LLM_CONFIG_FILE = settings.config_dir / "llm.yaml"


@dataclass
class LLMAdaptation:
    title: str | None = None
    profil: str | None = None
    competences: list[dict] | None = None
    bullets: dict[str, list[str]] = field(default_factory=dict)
    formation_bullets: dict[str, list[str]] = field(default_factory=dict)
    certifications: str | None = None
    langues: list[str] | None = None
    used_llm: bool = False
    warnings: list[str] = field(default_factory=list)


def load_llm_config() -> dict:
    if not LLM_CONFIG_FILE.exists():
        return {"enabled": False}
    with LLM_CONFIG_FILE.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    config["provider"] = os.getenv("CV_LLM_PROVIDER", config.get("provider", "ollama"))
    config["model"] = os.getenv("CV_LLM_MODEL", config.get("model", "glm-5.3-flash"))
    return config


def _llm_api_key() -> str:
    return (
        os.getenv("CV_LLM_API_KEY")
        or os.getenv("OLLAMA_API_KEY")
        or settings.ollama_api_key
        or ""
    ).strip()


def _cloud_model_name(model: str) -> str:
    """Sur ollama.com, le suffixe :cloud n'est pas nécessaire."""
    name = (model or "glm-5.3-flash").strip()
    if name.endswith(":cloud"):
        return name[: -len(":cloud")]
    return name


def _bullet_texts(exp: dict) -> list[str]:
    return [b if isinstance(b, str) else b["text"] for b in exp.get("bullets", [])]


def _compact_cv(cv_data: dict) -> dict:
    return {
        "title_default": cv_data["header"]["title_default"],
        "technos_root": cv_data.get("technos_root", []),
        "technos_extended": cv_data.get("technos_extended", []),
        "profil": cv_data.get("profil", {}).get("text", ""),
        "services": cv_data.get("profil", {}).get("services", []),
        "competences": cv_data.get("competences", []),
        "experiences": [
            {
                "id": exp["id"],
                "title": exp["title"],
                "company": exp["company"],
                "dates": exp["dates"],
                "bullets": _bullet_texts(exp),
            }
            for exp in cv_data.get("experiences", [])
        ],
        "formations": [
            {
                "id": f.get("id", f["school"]),
                "title": f["title"],
                "school": f["school"],
                "bullets": f.get("bullets", []),
            }
            for f in cv_data.get("formations", [])
        ],
        "certifications": cv_data.get("certifications", ""),
        "langues": cv_data.get("langues", []),
    }


def extract_job_brief(job: JobAnalysis) -> JobBrief:
    """Phase 1 — extraction structurée de l'offre (JSON / Pydantic)."""
    fallback = brief_from_heuristics(job)
    text = (job.cleaned or job.raw or "").strip()
    if len(text) < 20:
        return fallback
    config = load_llm_config()
    if not config.get("enabled", False):
        return fallback

    system = """Tu extrais un brief structuré depuis une offre d'emploi (souvent bruitée).
Réponds en JSON strict :
{
  "title": "...",
  "company": "... ou null",
  "keywords": ["..."],
  "hard_skills": ["..."],
  "soft_skills": ["..."],
  "missions": ["..."],
  "must_haves": ["..."]
}

- title : intitulé du POSTE, court, sans H/F, CDI, ville, salaire.
- company : employeur seulement, jamais l'intitulé. null si incertain.
- hard_skills : technos, outils, méthodes nommées (max 16).
- soft_skills : qualités humaines (max 8).
- keywords : mots-clés de ciblage (max 16).
- missions : 4 à 8 missions/attendus reformulés très court.
- must_haves : exigences indispensables (max 10).
N'invente rien qui n'est pas dans le texte."""

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "job_text": text[:10000],
                    "heuristic_title": job.title,
                    "heuristic_company": job.company,
                    "heuristic_tags": sorted(job.tags),
                },
                ensure_ascii=False,
            ),
        },
    ]
    try:
        raw = _call_llm(messages, config, temperature=0.15)
        brief = JobBrief.model_validate(_parse_json(raw))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError):
        return fallback

    if not brief.title:
        brief.title = fallback.title
    cfg = load_analysis_config()
    if brief.company and _looks_like_job_title(brief.company, cfg):
        brief.company = job.company
    if not brief.hard_skills and fallback.hard_skills:
        brief.hard_skills = fallback.hard_skills
    return brief


def apply_brief_to_analysis(job: JobAnalysis, brief: JobBrief) -> JobAnalysis:
    title = sanitize_cv_title(brief.title) if brief.title else job.title
    company = brief.company or job.company
    return JobAnalysis(
        raw=job.raw,
        cleaned=job.cleaned,
        source=job.source,
        company=company,
        title=title or job.title,
        tags=set(job.tags),
    )


def _job_expectations_hint(job: JobAnalysis) -> list[str]:
    """Extrait les lignes clés de l'offre pour guider le profil."""
    keywords = (
        "mission",
        "compétence",
        "competence",
        "profil",
        "recherch",
        "attendu",
        "responsabil",
        "vous ",
        "capacité",
        "maîtrise",
        "maitrise",
        "expérience",
        "experience",
    )
    hints: list[str] = []
    seen: set[str] = set()
    for line in job.cleaned.splitlines():
        stripped = line.strip().lstrip("*-•").strip()
        if len(stripped) < 12 or len(stripped) > 220:
            continue
        lower = stripped.lower()
        if lower in seen:
            continue
        if any(k in lower for k in keywords) or stripped.startswith(("-", "*", "•")):
            seen.add(lower)
            hints.append(stripped)
        if len(hints) >= 14:
            break
    return hints


def _skill_categories_hint(cv_data: dict | None = None) -> str:
    if cv_data:
        labels = [
            str(cat.get("label", "")).strip()
            for cat in cv_data.get("competences") or []
            if str(cat.get("label", "")).strip()
        ]
        if labels:
            return ", ".join(labels)
    return ", ".join(SKILL_CATEGORIES)


def _build_prompt(
    job: JobAnalysis,
    cv_data: dict,
    brief: JobBrief,
    match: MatchReport,
    *,
    english: bool,
) -> list[dict]:
    lang = "anglais" if english else "français"
    cats = _skill_categories_hint(cv_data)
    role = cv_data.get("header", {}).get("title_default") or "professionnel"
    inventory = collect_phrases(cv_data)
    system = f"""Tu adaptes un CV ({role}) à une offre, à partir d'un brief et d'un match déjà calculés.
Le PDF final DOIT tenir sur 1 page A4 — sois concis.

Réponds en JSON strict :
{{
  "title": "...",
  "profil": "...",
  "competences": [{{"label": "...", "items": ["...", "..."]}}],
  "bullets": {{"id_experience": ["...", "..."]}}
}}

Règle d'or : tu peux réordonner, reformuler ou accentuer, mais JAMAIS ajouter
une compétence, techno, outil, certification ou expérience absente de cv_data / inventory.
Les écarts (gaps) sont connus : ne les invente pas, ne les prétends pas maîtrisés.

Rapprochement sémantique : pour des tâches déjà présentes, réutilise le vocabulaire
exact de l'offre (vocabulary / emphasize).

- title : intitulé court (≤ 60 car.) aligné sur brief.title. Pas de H/F, CDI, ville.
- profil : 2 ou 3 phrases (200–320 car.), ton « ce que je fais », sans puces.
  Pas de tiret cadratin (—) ni demi-cadratin (–) : utilise : ou -.
- competences : EXACTEMENT ces libellés : {cats}.
  3–5 items courts, priorise emphasize. Interdit d'ajouter un gap.
- bullets : même nombre qu'à l'origine, ≤ 120 car., conserve [liens](url).
  Mets en avant ce qui recouvre emphasize / missions.

LANGUE : {lang}."""
    user = {
        "job_brief": brief.model_dump(),
        "match": {
            "score": match.score,
            "emphasize": match.emphasize,
            "gaps": match.gaps,
            "vocabulary": match.vocabulary,
        },
        "job_expectations": _job_expectations_hint(job),
        "job_text": job.cleaned[:6000],
        "inventory": inventory[:80],
        "cv_data": _compact_cv(cv_data),
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


def _http_error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace").strip()
    except Exception:
        body = ""
    return (body or exc.reason or str(exc))[:300]


def _call_llm(messages: list[dict], config: dict, *, temperature: float | None = None) -> str:
    api_key = _llm_api_key()
    if not api_key:
        raise urllib.error.URLError("Clé API absente (OLLAMA_API_KEY)")

    base_url = config.get("base_url", "https://ollama.com").rstrip("/")
    payload = {
        "model": _cloud_model_name(config.get("model", "glm-5.3-flash")),
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": float(
                temperature if temperature is not None else config.get("temperature", 0.5)
            )
        },
    }
    request = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request, timeout=int(config.get("timeout_seconds", 180))
        ) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise urllib.error.URLError(
            f"HTTP {exc.code}: {_http_error_detail(exc)}"
        ) from None

    content = (body.get("message") or {}).get("content") or ""
    content = str(content).strip()
    if not content:
        raise KeyError("Réponse LLM vide")
    return content


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _parse_competences(raw: object) -> list[dict] | None:
    if not isinstance(raw, list):
        return None
    parsed: list[dict] = []
    for cat in raw:
        if not isinstance(cat, dict):
            continue
        label = str(cat.get("label", "")).strip()
        items_raw = cat.get("items", [])
        if not label or not isinstance(items_raw, list):
            continue
        items = [str(i).strip() for i in items_raw if str(i).strip()]
        if items:
            parsed.append({"label": label, "items": items})
    return parsed or None


def _payload_from_raw(raw: dict) -> AdaptationPayload:
    return AdaptationPayload.model_validate(raw)


def _apply_payload(payload: dict | AdaptationPayload, cv_data: dict) -> LLMAdaptation:
    parsed = payload if isinstance(payload, AdaptationPayload) else _payload_from_raw(payload)
    result = LLMAdaptation(used_llm=True)
    exp_ids = {exp["id"] for exp in cv_data.get("experiences", [])}
    formation_ids = {f.get("id", f["school"]) for f in cv_data.get("formations", [])}

    title = sanitize_cv_title(parsed.title)
    if title:
        result.title = title[:90]
    else:
        result.warnings.append("Titre LLM vide — titre par défaut conservé.")

    profil = replace_long_dashes(parsed.profil)
    if profil:
        result.profil = profil[:500]

    result.competences = _parse_competences(
        [cat.model_dump() for cat in parsed.competences]
    )

    for exp_id, rewritten_list in parsed.bullets.items():
        if exp_id not in exp_ids:
            continue
        result.bullets[exp_id] = [
            replace_long_dashes(str(b).strip()) for b in rewritten_list if str(b).strip()
        ]

    for fid, rewritten_list in parsed.formation_bullets.items():
        if fid not in formation_ids:
            continue
        result.formation_bullets[fid] = [
            replace_long_dashes(str(b).strip()) for b in rewritten_list if str(b).strip()
        ]

    if parsed.certifications:
        result.certifications = replace_long_dashes(parsed.certifications)[:280]
    if parsed.langues:
        result.langues = [replace_long_dashes(lang) for lang in parsed.langues]

    return _ground_adaptation(result, cv_data)


def _source_bullets(exp: dict) -> list[str]:
    return [b if isinstance(b, str) else b["text"] for b in exp.get("bullets", [])]


def _ground_adaptation(result: LLMAdaptation, cv_data: dict) -> LLMAdaptation:
    """Retire les ajouts non ancrés dans le CV source et aligne le nombre de puces."""
    blob = collect_blob(cv_data)
    dropped = 0

    if result.competences:
        grounded_cats: list[dict] = []
        for cat in result.competences:
            items = []
            for item in cat.get("items") or []:
                if phrase_is_grounded(str(item), blob):
                    items.append(item)
                else:
                    dropped += 1
            if items:
                grounded_cats.append({"label": cat["label"], "items": items})
        result.competences = grounded_cats or None

    for exp in cv_data.get("experiences") or []:
        source = _source_bullets(exp)
        rewritten = result.bullets.get(exp["id"]) or []
        aligned: list[str] = []
        for idx, original in enumerate(source):
            candidate = rewritten[idx] if idx < len(rewritten) else original
            if phrase_is_grounded(candidate, blob):
                aligned.append(candidate)
            else:
                aligned.append(original)
                dropped += 1
        result.bullets[exp["id"]] = aligned

    if dropped:
        result.warnings.append(
            f"{dropped} reformulation(s) écartée(s) : hors inventaire du CV source."
        )
    return result


def _build_compress_prompt(
    cv_data: dict,
    current: LLMAdaptation,
    *,
    english: bool,
    attempt: int,
) -> list[dict]:
    lang = "anglais" if english else "français"
    cats = _skill_categories_hint(cv_data)
    system = f"""Tu compresses un CV pour qu'il tienne sur EXACTEMENT 1 page A4 PDF.
Toutes les sections doivent rester : Profil, Expériences, Formations, Compétences techniques,
Certifications, Langues. Ne supprime aucune section ni aucune expérience/formation.

Réponds en JSON strict :
{{
  "profil": "...",
  "competences": [{{"label": "...", "items": ["..."]}}],
  "bullets": {{"id_experience": ["..."]}},
  "formation_bullets": {{"id_formation": ["..."]}},
  "certifications": "...",
  "langues": ["...", "..."]
}}

Règles de compression (tentative {attempt}) :
- profil : 1–2 phrases littéraires (≤ 200 car.), humaines, sans puces.
- bullets : raccourcis (≤ 95 car. chacun), garde le même nombre par expérience, conserve [liens](url).
- competences : libellés EXACTS : {cats}. Max 4 items courts par catégorie.
- formation_bullets : 1 puce courte par formation.
- certifications : une ligne compacte.
- langues : formulations courtes.

Ne rien inventer. LANGUE : {lang}."""
    user = {
        "cv_data": _compact_cv(cv_data),
        "current_adaptation": {
            "title": current.title,
            "profil": current.profil,
            "competences": current.competences,
            "bullets": current.bullets,
            "formation_bullets": current.formation_bullets,
            "certifications": current.certifications,
            "langues": current.langues,
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


def _merge_adaptation(base: LLMAdaptation, update: LLMAdaptation) -> LLMAdaptation:
    merged = LLMAdaptation(
        title=base.title,
        profil=update.profil or base.profil,
        competences=update.competences or base.competences,
        bullets=base.bullets.copy(),
        formation_bullets=base.formation_bullets.copy(),
        certifications=update.certifications or base.certifications,
        langues=update.langues or base.langues,
        used_llm=True,
        warnings=list(base.warnings),
    )
    if update.bullets:
        merged.bullets.update(update.bullets)
    if update.formation_bullets:
        merged.formation_bullets.update(update.formation_bullets)
    return merged


def compress_cv_for_one_page(
    cv_data: dict,
    current: LLMAdaptation,
    *,
    english: bool = False,
    attempt: int = 1,
) -> LLMAdaptation | None:
    """Demande au LLM de raccourcir le contenu sans retirer de section."""
    config = load_llm_config()
    if not config.get("enabled", False):
        return None
    try:
        raw = _call_llm(
            _build_compress_prompt(cv_data, current, english=english, attempt=attempt),
            config,
            temperature=0.25,
        )
        compressed = _apply_payload(_parse_json(raw), cv_data)
        if not compressed.profil and not compressed.bullets and not compressed.competences:
            return None
        return _merge_adaptation(current, compressed)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
        current.warnings.append(f"Compression LLM échouée ({exc}).")
        return None


def adapt_with_llm(
    job: JobAnalysis,
    cv_data: dict,
    *,
    brief: JobBrief | None = None,
    match: MatchReport | None = None,
    force: bool = False,
    english: bool = False,
) -> LLMAdaptation | None:
    config = load_llm_config()
    if not force and not config.get("enabled", False):
        return None
    resolved_brief = brief or brief_from_heuristics(job)
    resolved_match = match
    if resolved_match is None:
        from app.services.matching import score_match

        resolved_match = score_match(cv_data, job, resolved_brief)
    try:
        raw = _call_llm(
            _build_prompt(job, cv_data, resolved_brief, resolved_match, english=english),
            config,
            temperature=float(config.get("temperature", 0.45)),
        )
        return _apply_payload(_parse_json(raw), cv_data)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
        return LLMAdaptation(used_llm=False, warnings=[f"LLM indisponible ({exc})."])


def check_llm_status() -> dict:
    config = load_llm_config()
    model = _cloud_model_name(config.get("model", "glm-5.3-flash"))
    base_url = config.get("base_url", "https://ollama.com").rstrip("/")
    result = {
        "enabled": bool(config.get("enabled", False)),
        "provider": config.get("provider", "ollama"),
        "model": model,
        "base_url": base_url,
        "server_ok": False,
        "model_ready": False,
        "message": "",
    }
    if not _llm_api_key():
        result["message"] = "Clé API absente. Définis OLLAMA_API_KEY dans .env"
        return result
    try:
        request = urllib.request.Request(
            f"{base_url}/api/tags",
            method="GET",
            headers={"Authorization": f"Bearer {_llm_api_key()}"},
        )
        with urllib.request.urlopen(request, timeout=10) as resp:
            resp.read()
        result["server_ok"] = True
        result["model_ready"] = True
        result["message"] = f"Ollama Cloud OK — {model}"
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            result["message"] = "Clé API Ollama invalide ou refusée."
        elif exc.code == 404:
            result["server_ok"] = True
            result["model_ready"] = True
            result["message"] = f"Ollama Cloud OK — {model}"
        else:
            result["message"] = f"API Ollama HTTP {exc.code}: {_http_error_detail(exc)}"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
        result["message"] = f"API Ollama Cloud inaccessible ({exc})."
    return result
