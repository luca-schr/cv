"""Réécriture intelligente via LLM avec garde-fous factuels."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from cv_builder.guardrails import (
    build_allowed_vocabulary,
    validate_bullet_rewrite,
    validate_profil,
    validate_title,
)
from cv_builder.job_analyzer import JobAnalysis

ROOT = Path(__file__).resolve().parent.parent
LLM_CONFIG_FILE = ROOT / "config" / "llm.yaml"


@dataclass
class LLMAdaptation:
    title: str | None = None
    profil: str | None = None
    experience_order: list[str] = field(default_factory=list)
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
    if os.getenv("OPENAI_API_KEY"):
        config.setdefault("provider", "openai")
    return config


def _compact_cv_for_prompt(cv_data: dict) -> dict:
    return {
        "title_default": cv_data["header"]["title_default"],
        "profil_intro": cv_data["profil"]["intro"],
        "profil_closing": cv_data["profil"]["closing"],
        "keywords": [item["term"] for item in cv_data["profil"]["keywords"]],
        "experiences": [
            {
                "id": exp["id"],
                "title": exp["title"],
                "company": exp["company"],
                "dates": exp["dates"],
                "bullets": [bullet["text"] for bullet in exp["bullets"]],
            }
            for exp in cv_data["experiences"]
        ],
        "competences": [
            f"{cat['label']}: {', '.join(i['term'] for i in cat['items'])}"
            for cat in cv_data["competences"]
        ],
        "formations": [
            f"{f['title']} - {f['school']} ({f['dates']})"
            for f in cv_data["formations"]
        ],
    }


def _build_prompt(job: JobAnalysis, cv_data: dict) -> list[dict]:
    system = """Tu adaptes un CV à une offre d'emploi.

RÈGLES STRICTES :
- N'invente AUCUNE expérience, mission, techno, certification ou date.
- Utilise UNIQUEMENT les faits du JSON cv_data.
- Tu peux reformuler et réordonner pour coller au vocabulaire de l'offre.
- Conserve les liens Markdown [texte](url) des bullets d'origine si tu réécris une bullet.
- Réponds UNIQUEMENT en JSON valide, sans markdown autour.

Schéma JSON attendu :
{
  "title": "intitulé court aligné sur l'offre",
  "profil": "2 phrases max, ton professionnel",
  "experience_order": ["id1", "id2", ...],
  "bullets": {
    "id_experience": ["bullet reformulée 1", "bullet reformulée 2"]
  }
}

experience_order : tous les id de cv_data.experiences, les plus pertinents en premier.
bullets : pour chaque expérience, même nombre de bullets que la source, même ordre de sens (pertinent en premier)."""

    user = {
        "job_title_detected": job.title,
        "job_tags": sorted(job.tags),
        "job_text": job.cleaned[:6000],
        "cv_data": _compact_cv_for_prompt(cv_data),
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False, indent=2)},
    ]


def _call_ollama(messages: list[dict], config: dict) -> str:
    base_url = config.get("base_url", "http://localhost:11434").rstrip("/")
    payload = {
        "model": config.get("model", "llama3.2"),
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {"temperature": float(config.get("temperature", 0.2))},
    }
    request = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout = int(config.get("timeout_seconds", 120))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body["message"]["content"]


def _call_openai(messages: list[dict], config: dict) -> str:
    api_key = os.environ["OPENAI_API_KEY"]
    payload = {
        "model": config.get("openai_model", "gpt-4o-mini"),
        "messages": messages,
        "temperature": float(config.get("temperature", 0.2)),
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    timeout = int(config.get("timeout_seconds", 120))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def _call_llm(messages: list[dict], config: dict) -> str:
    provider = config.get("provider", "ollama")
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY manquant pour provider openai")
        return _call_openai(messages, config)
    return _call_ollama(messages, config)


def _parse_llm_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def _apply_guardrails(payload: dict, cv_data: dict, fallback_title: str) -> LLMAdaptation:
    allowed = build_allowed_vocabulary(cv_data)
    exp_by_id = {exp["id"]: exp for exp in cv_data["experiences"]}
    result = LLMAdaptation(used_llm=True)

    title = str(payload.get("title", "")).strip()
    if validate_title(title):
        result.title = title
    else:
        result.warnings.append("Titre LLM rejeté, titre analysé conservé.")

    profil = str(payload.get("profil", "")).strip()
    if validate_profil(profil, allowed):
        result.profil = profil
    else:
        result.warnings.append("Profil LLM rejeté, version par mots-clés conservée.")

    order = payload.get("experience_order", [])
    if isinstance(order, list):
        valid_order = [exp_id for exp_id in order if exp_id in exp_by_id]
        missing = [exp_id for exp_id in exp_by_id if exp_id not in valid_order]
        if valid_order and len(valid_order) + len(missing) == len(exp_by_id):
            result.experience_order = valid_order + missing
        else:
            result.warnings.append("Ordre des expériences LLM invalide, tri par tags conservé.")

    bullets_payload = payload.get("bullets", {})
    if isinstance(bullets_payload, dict):
        for exp_id, rewritten_list in bullets_payload.items():
            if exp_id not in exp_by_id or not isinstance(rewritten_list, list):
                continue
            originals = [bullet["text"] for bullet in exp_by_id[exp_id]["bullets"]]
            if len(rewritten_list) != len(originals):
                result.warnings.append(f"Bullets {exp_id} : nombre incorrect, source conservée.")
                continue
            accepted: list[str] = []
            for rewritten, original in zip(rewritten_list, originals):
                text = str(rewritten).strip()
                if validate_bullet_rewrite(text, original, allowed):
                    accepted.append(text)
                else:
                    accepted.append(original)
                    result.warnings.append(f"Bullet {exp_id} rejetée, texte source conservé.")
            result.bullets[exp_id] = accepted

    if not result.title:
        result.title = fallback_title
    return result


def adapt_with_llm(job: JobAnalysis, cv_data: dict, *, force: bool = False) -> LLMAdaptation | None:
    config = load_llm_config()
    if not force and not config.get("enabled", False):
        return None

    messages = _build_prompt(job, cv_data)
    try:
        raw = _call_llm(messages, config)
        payload = _parse_llm_json(raw)
        return _apply_guardrails(payload, cv_data, job.title)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, RuntimeError) as exc:
        warning = LLMAdaptation(used_llm=False, warnings=[f"LLM indisponible ({exc}), mode règles."])
        return warning
