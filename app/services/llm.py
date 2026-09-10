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
from app.services.analyzer import JobAnalysis
from app.services.competences import SKILL_CATEGORIES
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


@dataclass
class JobMetaExtraction:
    title: str | None = None
    company: str | None = None
    used_llm: bool = False


def extract_job_meta_with_llm(cleaned: str) -> JobMetaExtraction | None:
    """Extrait intitulé de poste et employeur depuis la fiche (LLM)."""
    text = (cleaned or "").strip()
    if len(text) < 20:
        return None
    config = load_llm_config()
    if not config.get("enabled", False):
        return None

    system = """Tu extrais les métadonnées d'une offre d'emploi collée (souvent bruitée).
Réponds en JSON strict : {"job_title": "...", "company": "..."}

- job_title : intitulé du POSTE offert.
  • Si un titre explicite existe (en-tête, « poste », première ligne métier), reprends-le nettoyé.
  • Sinon déduis un intitulé court et fidèle depuis missions + compétences (≤ 80 car.).
  • Retire H/F, CDI, CDD, alternance, ville, salaire. Garde les technos si pertinentes.

- company : nom court de l'EMPLOYEUR (entreprise, agence, administration).
  • Cherche : Employeur, Entreprise, Société, « chez … », sigle entre parenthèses (ex. ECPAD).
  • Ne confonds PAS intitulé de poste et employeur.
  • null si introuvable ou incertain."""

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps({"job_text": text[:10000]}, ensure_ascii=False)},
    ]
    try:
        raw = _call_llm(messages, config, temperature=0.15)
        payload = _parse_json(raw)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
        return JobMetaExtraction(used_llm=False)

    title = sanitize_cv_title(str(payload.get("job_title") or payload.get("title") or "").strip())
    company_raw = payload.get("company")
    company = None
    if company_raw is not None and str(company_raw).strip().lower() not in ("null", "none", ""):
        company = re.sub(r"\s{2,}", " ", str(company_raw).strip())[:80]

    return JobMetaExtraction(
        title=title[:90] if title else None,
        company=company,
        used_llm=True,
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


def _build_prompt(job: JobAnalysis, cv_data: dict, *, english: bool) -> list[dict]:
    lang = "anglais" if english else "français"
    cats = _skill_categories_hint(cv_data)
    role = cv_data.get("header", {}).get("title_default") or "professionnel"
    system = f"""Tu adaptes un CV ({role}) à une offre d'emploi.
Le PDF final DOIT tenir sur 1 page A4 — sois concis.

Réponds en JSON strict :
{{
  "title": "...",
  "profil": "...",
  "competences": [{{"label": "...", "items": ["...", "..."]}}],
  "bullets": {{"id_experience": ["...", "..."]}}
}}

Consignes :
- title : intitulé court (≤ 60 car.) aligné sur l'offre. Pas de H/F, CDI, localisation.

- profil : 2 ou 3 phrases littéraires et humaines (200–320 car.), ton « ce que je fais ».
  Pas de liste à puces. Pas de tiret cadratin (—) ni demi-cadratin (–) : utilise : ou -.
  Décris ton approche et ta valeur ajoutée, reliée à l'offre.
  Ex. : « Je conçois et livre… en gardant le fil entre besoin métier, code et mise en production. »
  Ne rien inventer hors cv_data.

- competences : EXACTEMENT ces libellés (dans cet ordre si pertinent) : {cats}.
  3–5 items courts par catégorie. Priorise les compétences de l'offre.

- bullets : reformule les missions (même nombre qu'à l'origine), phrases courtes (≤ 120 car.).
  Conserve les liens [texte](url). Mets en avant ce qui répond à l'offre.

Reste crédible. LANGUE : {lang}."""
    user = {
        "job_title_detected": job.title,
        "job_company": job.company,
        "job_tags": sorted(job.tags),
        "job_expectations": _job_expectations_hint(job),
        "job_text": job.cleaned[:8000],
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


def _apply_payload(payload: dict, cv_data: dict) -> LLMAdaptation:
    result = LLMAdaptation(used_llm=True)
    exp_ids = {exp["id"] for exp in cv_data.get("experiences", [])}
    formation_ids = {
        f.get("id", f["school"]) for f in cv_data.get("formations", [])
    }

    title = sanitize_cv_title(str(payload.get("title", "")).strip())
    if title:
        result.title = title[:90]
    elif "title" in payload:
        result.warnings.append("Titre LLM vide — titre par défaut conservé.")

    profil = replace_long_dashes(str(payload.get("profil", "")).strip())
    if profil:
        result.profil = profil[:500]

    result.competences = _parse_competences(payload.get("competences"))

    bullets_payload = payload.get("bullets", {})
    if isinstance(bullets_payload, dict):
        for exp_id, rewritten_list in bullets_payload.items():
            if exp_id not in exp_ids or not isinstance(rewritten_list, list):
                continue
            result.bullets[exp_id] = [
                replace_long_dashes(str(b).strip())
                for b in rewritten_list
                if str(b).strip()
            ]

    formation_payload = payload.get("formation_bullets", {})
    if isinstance(formation_payload, dict):
        for fid, rewritten_list in formation_payload.items():
            if fid not in formation_ids or not isinstance(rewritten_list, list):
                continue
            result.formation_bullets[fid] = [
                replace_long_dashes(str(b).strip())
                for b in rewritten_list
                if str(b).strip()
            ]

    certs = replace_long_dashes(str(payload.get("certifications", "")).strip())
    if certs:
        result.certifications = certs[:280]

    langues_raw = payload.get("langues")
    if isinstance(langues_raw, list):
        result.langues = [
            replace_long_dashes(str(lang).strip())
            for lang in langues_raw
            if str(lang).strip()
        ]

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
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
        current.warnings.append(f"Compression LLM échouée ({exc}).")
        return None


def adapt_with_llm(
    job: JobAnalysis, cv_data: dict, *, force: bool = False, english: bool = False
) -> LLMAdaptation | None:
    config = load_llm_config()
    if not force and not config.get("enabled", False):
        return None
    try:
        raw = _call_llm(
            _build_prompt(job, cv_data, english=english),
            config,
            temperature=float(config.get("temperature", 0.45)),
        )
        return _apply_payload(_parse_json(raw), cv_data)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
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
