"""Adaptation CV via Ollama."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from app.config import settings
from app.services.sanitize import sanitize_cv_title

LLM_CONFIG_FILE = settings.config_dir / "llm.yaml"


@dataclass
class JobAnalysis:
    company: str | None
    job_title: str
    categories: list[dict] = field(default_factory=list)


@dataclass
class CvAdaptation:
    title: str | None = None
    profil: str | None = None
    bullets: dict[str, list[str]] = field(default_factory=dict)
    formation_bullets: dict[str, list[str]] = field(default_factory=dict)
    skill_groups: list[dict] = field(default_factory=list)
    certifications: str | None = None
    langues: list[str] | None = None
    warnings: list[str] = field(default_factory=list)


def load_llm_config() -> dict:
    if not LLM_CONFIG_FILE.exists():
        return {"enabled": False}
    with LLM_CONFIG_FILE.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    config["provider"] = os.getenv("CV_LLM_PROVIDER", config.get("provider", "ollama"))
    config["model"] = os.getenv("CV_LLM_MODEL", config.get("model", "llama3.2"))
    config["base_url"] = os.getenv(
        "CV_LLM_BASE_URL", config.get("base_url", "http://localhost:11434")
    )
    return config


def _call_ollama(messages: list[dict], config: dict, *, temperature: float) -> str:
    base_url = config.get("base_url", "http://localhost:11434").rstrip("/")
    payload = {
        "model": config.get("model", "llama3.2"),
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {"temperature": float(temperature)},
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


def check_ollama_status() -> dict:
    config = load_llm_config()
    model = config.get("model", "llama3.2")
    base_url = config.get("base_url", "http://localhost:11434").rstrip("/")
    result = {
        "enabled": bool(config.get("enabled", False)),
        "model": model,
        "base_url": base_url,
        "server_ok": False,
        "model_ready": False,
        "message": "Ollama : vérification…",
    }
    if not result["enabled"]:
        result["message"] = "Ollama désactivé (config/llm.yaml)"
        return result

    try:
        request = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=2) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        result["server_ok"] = True
        installed = {m.get("name", "").split(":")[0] for m in body.get("models", [])}
        result["model_ready"] = model in installed
        if result["model_ready"]:
            result["message"] = f"Ollama OK — {model}"
        else:
            result["message"] = f"Modèle absent — ollama pull {model}"
    except (urllib.error.URLError, TimeoutError, OSError):
        result["message"] = "Ollama inaccessible — lance ollama serve"
    return result


def analyze_job(job_text: str, *, temperature: float = 0.2) -> JobAnalysis:
    config = load_llm_config()
    if not config.get("enabled", False):
        raise RuntimeError("Ollama désactivé dans config/llm.yaml")

    system = """Tu analyses une fiche de poste (souvent bruitée).
Réponds en JSON strict :
{
  "company": "... ou null",
  "job_title": "...",
  "categories": [{"name": "...", "skills": ["...", "..."]}]
}

- company : employeur court si identifiable, sinon null.
- job_title : intitulé du poste si présent, sinon titre court déduit des missions (≤ 80 car.).
- categories : regroupe les technos/compétences citées dans l'offre en catégories libres (pas de liste fixe).
  Inclus uniquement les skills mentionnées ou clairement requises. skills sans niveau."""

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps({"job_text": job_text[:10000]}, ensure_ascii=False)},
    ]
    raw = _call_ollama(messages, config, temperature=min(temperature, 0.25))
    payload = _parse_json(raw)
    company = payload.get("company")
    if company is not None and str(company).strip().lower() in ("null", "none", ""):
        company = None
    elif company:
        company = str(company).strip()[:80]

    title = sanitize_cv_title(str(payload.get("job_title", "")).strip() or "Développeur")
    categories = payload.get("categories") if isinstance(payload.get("categories"), list) else []
    clean_cats: list[dict] = []
    for block in categories:
        if not isinstance(block, dict):
            continue
        name = str(block.get("name", "")).strip()
        skills = [str(s).strip() for s in block.get("skills", []) if str(s).strip()]
        if name and skills:
            clean_cats.append({"name": name, "skills": skills})

    return JobAnalysis(company=company, job_title=title, categories=clean_cats)


def adapt_cv(
    *,
    profile_data: dict,
    skills_snapshot: list[dict],
    job_analysis: JobAnalysis,
    job_text: str,
    relevant_subskills: list[dict] | None = None,
    subskill_hints: list[str] | None = None,
    title_technologies: list[str] | None = None,
    temperature: float = 0.45,
    english: bool = False,
) -> CvAdaptation:
    config = load_llm_config()
    lang = "anglais" if english else "français"
    strong = [
        s["name"]
        for block in skills_snapshot
        for s in block.get("skills", [])
        if s.get("level") is not None and s["level"] >= 4
    ]
    preferred = [
        s["name"]
        for block in skills_snapshot
        for s in block.get("skills", [])
        if s.get("preferred")
    ]
    title_techs = title_technologies or []
    exp_ids = [e["id"] for e in profile_data.get("experiences", [])]
    hints_block = ""
    if subskill_hints:
        hints_block = (
            "\nSubskills à afficher en complément des skills parentes (format « Parent — sub1, sub2 ») :\n"
            + "\n".join(subskill_hints[:14])
        )
    title_block = ""
    if title_techs:
        title_block = (
            f"\nTechnos détectées dans le TITRE du poste : {', '.join(title_techs)}. "
            "Elles DOIVENT apparaître dans skill_groups et orienter profil + expériences."
        )

    system = f"""Tu adaptes un CV développeur à une offre. Le PDF final DOIT tenir sur 1 page A4.

Réponds en JSON strict :
{{
  "title": "...",
  "profil": "...",
  "skill_groups": [{{"label": "...", "items": ["...", "..."]}}],
  "bullets": {{"id_experience": ["...", "..."]}}
}}

Règles :
- title : court (≤ 60 car.), aligné sur l'offre sans inventer de techno non documentée.
- profil : RÉÉCRIS 2-3 phrases pour CETTE offre précise (pas de texte générique). Langage littéraire, sans puces.
  Intègre le poste « {job_analysis.job_title} » et les technos fortes : {strong[:10]}.
  Mets en avant les technos préférées compatibles : {preferred[:10]}.{title_block}
  Ne prétends pas maîtriser une techno absente du profil (level null = transfert honnête uniquement).
- skill_groups : affiche skills ET subskills. Format obligatoire : « Parent — sub1, sub2 » (ex. React — TanStack Query, Hooks).
  Inclus les technos du titre du poste. Priorise les subskills listées ci-dessous.{hints_block}
- bullets : RÉÉCRIS les missions pour CETTE offre (ids expériences : {exp_ids}). Même nombre de puces par expérience.
  ≤ 120 car., garde [liens](url). Angle et vocabulaire adaptés au poste — ne recopie pas le corpus tel quel.
  Mets en avant les expériences dont le stack correspond au titre et à l'offre.

LANGUE : {lang}."""

    user = {
        "job_title": job_analysis.job_title,
        "job_company": job_analysis.company,
        "job_categories": job_analysis.categories,
        "job_text": job_text[:8000],
        "title_technologies": title_techs,
        "profile": profile_data,
        "skills": skills_snapshot,
        "relevant_subskills": relevant_subskills or [],
    }
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]
    raw = _call_ollama(messages, config, temperature=temperature)
    payload = _parse_json(raw)
    return _payload_to_adaptation(payload, profile_data)


def compress_cv(
    *,
    profile_data: dict,
    current: CvAdaptation,
    attempt: int,
    temperature: float = 0.25,
    english: bool = False,
) -> CvAdaptation:
    config = load_llm_config()
    lang = "anglais" if english else "français"
    system = f"""Tu compresses un CV pour EXACTEMENT 1 page A4 PDF.
Garde toutes les sections. Réponds en JSON :
{{
  "profil": "...",
  "skill_groups": [{{"label": "...", "items": ["..."]}}],
  "bullets": {{"id_experience": ["..."]}},
  "formation_bullets": {{"id_formation": ["..."]}},
  "certifications": "...",
  "langues": ["..."]
}}

Tentative {attempt} : raccourcis (profil ≤ 200 car., bullets ≤ 95 car., max 3 items/skill_group).
LANGUE : {lang}."""

    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "profile": profile_data,
                    "current": {
                        "title": current.title,
                        "profil": current.profil,
                        "skill_groups": current.skill_groups,
                        "bullets": current.bullets,
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]
    raw = _call_ollama(messages, config, temperature=temperature)
    payload = _parse_json(raw)
    merged = _payload_to_adaptation(payload, profile_data)
    merged.title = current.title
    if not merged.profil:
        merged.profil = current.profil
    if not merged.bullets:
        merged.bullets = current.bullets
    if not merged.skill_groups:
        merged.skill_groups = current.skill_groups
    return merged


def _payload_to_adaptation(payload: dict, profile_data: dict) -> CvAdaptation:
    result = CvAdaptation()
    title = sanitize_cv_title(str(payload.get("title", "")).strip())
    if title:
        result.title = title[:90]

    profil = str(payload.get("profil", "")).strip()
    if profil:
        result.profil = profil[:500]

    exp_ids = {e["id"] for e in profile_data.get("experiences", [])}
    bullets = payload.get("bullets", {})
    if isinstance(bullets, dict):
        for eid, items in bullets.items():
            if eid in exp_ids and isinstance(items, list):
                result.bullets[eid] = [str(b).strip() for b in items if str(b).strip()]

    groups = payload.get("skill_groups") or payload.get("competences")
    if isinstance(groups, list):
        for g in groups:
            if not isinstance(g, dict):
                continue
            label = str(g.get("label", "")).strip()
            items_raw = g.get("items", g.get("skills", []))
            if label and isinstance(items_raw, list):
                items = [str(i).strip() for i in items_raw if str(i).strip()]
                if items:
                    result.skill_groups.append({"label": label, "items": items})

    certs = str(payload.get("certifications", "")).strip()
    if certs:
        result.certifications = certs[:280]

    langues = payload.get("langues")
    if isinstance(langues, list):
        result.langues = [str(l).strip() for l in langues if str(l).strip()]

    return result
