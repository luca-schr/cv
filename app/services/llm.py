"""Adaptation CV via Ollama — prompt ouvert, peu de contraintes."""

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
from app.services.sanitize import sanitize_cv_title

LLM_CONFIG_FILE = settings.config_dir / "llm.yaml"


@dataclass
class LLMAdaptation:
    title: str | None = None
    profil: str | None = None
    competences: list[dict] | None = None
    bullets: dict[str, list[str]] = field(default_factory=dict)
    used_llm: bool = False
    warnings: list[str] = field(default_factory=list)


def load_llm_config() -> dict:
    if not LLM_CONFIG_FILE.exists():
        return {"enabled": False}
    with LLM_CONFIG_FILE.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    config["provider"] = os.getenv("CV_LLM_PROVIDER", config.get("provider", "ollama"))
    config["model"] = os.getenv("CV_LLM_MODEL", config.get("model", "llama3.2"))
    return config


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
    }


@dataclass
class JobMetaExtraction:
    title: str | None = None
    company: str | None = None
    used_llm: bool = False


def extract_job_meta_with_llm(cleaned: str) -> JobMetaExtraction | None:
    """Extrait intitulé de poste et employeur depuis la fiche (Ollama)."""
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
        raw = _call_ollama(messages, config, temperature=0.15)
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


def _build_prompt(job: JobAnalysis, cv_data: dict, *, english: bool) -> list[dict]:
    lang = "anglais" if english else "français"
    system = f"""Tu adaptes un CV développeur fullstack à une offre d'emploi.
Réponds en JSON strict :
{{
  "title": "...",
  "profil": "...",
  "competences": [{{"label": "...", "items": ["...", "..."]}}],
  "bullets": {{"id_experience": ["...", "..."]}}
}}

Consignes :
- title : intitulé court (≤ 60 car.) aligné sur l'offre. Pas de H/F, CDI, localisation.

- profil : EXACTEMENT 2 ou 3 phrases (280–420 car.), comme une réponse directe à la fiche de poste.
  Le candidat propose des prestations (voir services dans cv_data) : apps React/Next, API Node, WordPress, CI/CD.
  Structure obligatoire :
  • Phrase 1 : alignement sur le rôle et le contexte de l'annonce (secteur, type de produit, missions).
    Reprends 2–4 termes ou expressions de job_text / job_expectations.
  • Phrase 2 : relie les besoins concrets de l'offre (missions, compétences attendues, job_tags)
    aux expériences et technos RÉELLES du candidat dans cv_data.
  • Phrase 3 (si utile) : atout complémentaire crédible (maintenance, déploiement, autonomie, équipe…)
    UNIQUEMENT si l'offre le valorise et que le CV le justifie.
  Règles profil : ne rien inventer hors cv_data ; pas de liste à puces ; ton professionnel et concret ;
  chaque phrase doit pouvoir se justifier par une mission ou une techno de l'offre ET du CV.

- competences : réorganise et détaille technos_root + technos_extended (sous-compétences OK :
  ex. React → Hooks, TanStack Query ; Node → Express, NestJS, middleware, auth).
  Priorise les technos citées dans l'offre. Garde 3–6 catégories, 4–6 items détaillés par catégorie.
- bullets : reformule les missions par expérience (même nombre qu'à l'origine).
  Mets en avant ce qui répond à l'offre. Conserve les liens [texte](url).
  L'ordre des expériences ne change pas.

Reste crédible par rapport au parcours fourni. LANGUE : {lang}."""
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


def _call_ollama(messages: list[dict], config: dict, *, temperature: float | None = None) -> str:
    base_url = config.get("base_url", "http://localhost:11434").rstrip("/")
    payload = {
        "model": config.get("model", "llama3.2"),
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {"temperature": float(temperature if temperature is not None else config.get("temperature", 0.6))},
    }
    request = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=int(config.get("timeout_seconds", 120))) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["message"]["content"]


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


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

    title = sanitize_cv_title(str(payload.get("title", "")).strip())
    if title:
        result.title = title[:90]
    else:
        result.warnings.append("Titre LLM vide — titre par défaut conservé.")

    profil = str(payload.get("profil", "")).strip()
    if profil:
        result.profil = profil[:500]
    else:
        result.warnings.append("Profil LLM vide — texte par défaut conservé.")

    result.competences = _parse_competences(payload.get("competences"))

    bullets_payload = payload.get("bullets", {})
    if isinstance(bullets_payload, dict):
        for exp_id, rewritten_list in bullets_payload.items():
            if exp_id not in exp_ids or not isinstance(rewritten_list, list):
                continue
            result.bullets[exp_id] = [str(b).strip() for b in rewritten_list if str(b).strip()]

    return result


def adapt_with_llm(
    job: JobAnalysis, cv_data: dict, *, force: bool = False, english: bool = False
) -> LLMAdaptation | None:
    config = load_llm_config()
    if not force and not config.get("enabled", False):
        return None
    try:
        raw = _call_ollama(
            _build_prompt(job, cv_data, english=english),
            config,
            temperature=float(config.get("temperature", 0.45)),
        )
        return _apply_payload(_parse_json(raw), cv_data)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
        return LLMAdaptation(used_llm=False, warnings=[f"LLM indisponible ({exc})."])


def check_ollama_status() -> dict:
    config = load_llm_config()
    model = config.get("model", "llama3.2")
    base_url = config.get("base_url", "http://localhost:11434").rstrip("/")
    result = {
        "enabled": bool(config.get("enabled", False)),
        "provider": config.get("provider", "ollama"),
        "model": model,
        "base_url": base_url,
        "server_ok": False,
        "model_ready": False,
        "message": "",
    }
    try:
        request = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        result["server_ok"] = True
        installed = {m.get("name", "").split(":")[0] for m in body.get("models", [])}
        result["model_ready"] = model in installed
        if result["model_ready"]:
            result["message"] = f"Ollama OK — modèle {model} disponible"
        else:
            result["message"] = f"Ollama actif mais modèle '{model}' absent. Lance : ollama pull {model}"
    except (urllib.error.URLError, TimeoutError) as exc:
        result["message"] = f"Ollama inaccessible ({exc}). Lance l'app Ollama."
    return result
