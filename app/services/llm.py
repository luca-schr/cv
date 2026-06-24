"""Réécriture via Ollama avec garde-fous."""

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
from app.services.analyzer import JobAnalysis, load_analysis_config
from app.services.guardrails import (
    build_allowed_vocabulary,
    validate_bullet_rewrite,
    validate_profil,
)

LLM_CONFIG_FILE = settings.config_dir / "llm.yaml"


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
    return config


def _compact_cv(cv_data: dict) -> dict:
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
                "bullets": [b["text"] for b in exp["bullets"]],
            }
            for exp in cv_data["experiences"]
        ],
    }


def _build_prompt(job: JobAnalysis, cv_data: dict) -> list[dict]:
    from app.services.title_resolver import resolve_title

    canonical = resolve_title(cv_data, job.tags, job.title)
    system = """Tu adaptes un CV à une offre. N'invente rien. Utilise uniquement cv_data.
NE COPIE PAS l'intitulé de l'offre. Le titre du CV est déjà fixé.
L'ordre des expériences est chronologique (ne pas réordonner).
Réponds en JSON : {"profil","bullets":{"id":["..."]}}
- profil : 2 phrases max, vocabulaire de l'offre, faits du CV uniquement
- bullets : missions impactantes et concises, reformuler sans inventer, conserver les liens [texte](url)"""
    user = {
        "cv_title_fixed": canonical,
        "job_tags": sorted(job.tags),
        "job_text": job.cleaned[:6000],
        "cv_data": _compact_cv(cv_data),
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
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
    with urllib.request.urlopen(request, timeout=int(config.get("timeout_seconds", 120))) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["message"]["content"]


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def _apply_guardrails(payload: dict, cv_data: dict) -> LLMAdaptation:
    allowed = build_allowed_vocabulary(cv_data)
    exp_by_id = {exp["id"]: exp for exp in cv_data["experiences"]}
    result = LLMAdaptation(used_llm=True)

    profil = str(payload.get("profil", "")).strip()
    max_chars = int(load_analysis_config().get("scoring", {}).get("profil_max_chars", 380))
    if validate_profil(profil, allowed, max_chars):
        result.profil = profil
    else:
        result.warnings.append("Profil LLM rejeté.")

    bullets_payload = payload.get("bullets", {})
    if isinstance(bullets_payload, dict):
        for exp_id, rewritten_list in bullets_payload.items():
            if exp_id not in exp_by_id or not isinstance(rewritten_list, list):
                continue
            originals = [b["text"] for b in exp_by_id[exp_id]["bullets"]]
            if len(rewritten_list) != len(originals):
                result.warnings.append(f"Bullets {exp_id} : nombre incorrect.")
                continue
            accepted = []
            for rewritten, original in zip(rewritten_list, originals):
                text = str(rewritten).strip()
                if validate_bullet_rewrite(text, original, allowed):
                    accepted.append(text)
                else:
                    accepted.append(original)
                    result.warnings.append(f"Bullet {exp_id} rejetée.")
            result.bullets[exp_id] = accepted
    return result


def adapt_with_llm(job: JobAnalysis, cv_data: dict, *, force: bool = False) -> LLMAdaptation | None:
    config = load_llm_config()
    if not force and not config.get("enabled", False):
        return None
    try:
        raw = _call_ollama(_build_prompt(job, cv_data), config)
        return _apply_guardrails(_parse_json(raw), cv_data)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
        return LLMAdaptation(used_llm=False, warnings=[f"LLM indisponible ({exc})."])


def check_ollama_status() -> dict:
    """Vérifie que le serveur Ollama tourne et que le modèle configuré est présent."""
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
