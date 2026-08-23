"""Client Ollama + chargement config/llm.yaml."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx
import yaml

from app.config import settings


def load_llm_config() -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "enabled": False,
        "provider": "ollama",
        "model": "llama3.2",
        "base_url": "http://localhost:11434",
        "timeout_seconds": 25,
    }
    config_path: Path = settings.llm_config_path
    if not config_path.exists():
        return defaults
    try:
        parsed = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(parsed, dict):
            return defaults
        return {**defaults, **parsed}
    except (OSError, yaml.YAMLError):
        return defaults


def llm_is_usable(status: dict[str, Any] | None) -> bool:
    if not status:
        return False
    return bool(status.get("enabled") and status.get("server_ok") and status.get("model_ready"))


def _model_is_installed(model: str, names: list[str]) -> bool:
    wanted = (model or "").strip()
    if not wanted:
        return False
    if wanted in names:
        return True
    base = wanted.split(":")[0]
    return any(n == base or n.split(":")[0] == base for n in names)


async def check_ollama_status() -> dict[str, Any]:
    config = load_llm_config()
    model = str(config.get("model") or "llama3.2")
    base_url = str(config.get("base_url") or "http://localhost:11434").rstrip("/")
    result: dict[str, Any] = {
        "enabled": bool(config.get("enabled")),
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
        async with httpx.AsyncClient(timeout=2.5) as client:
            res = await client.get(f"{base_url}/api/tags")
            res.raise_for_status()
            body = res.json()
        result["server_ok"] = True
        names = [str(m.get("name") or "") for m in (body.get("models") or [])]
        result["model_ready"] = _model_is_installed(model, names)
        result["message"] = (
            f"Ollama OK — {model}"
            if result["model_ready"]
            else f"Modèle absent — ollama pull {model}"
        )
    except httpx.ConnectError:
        result["message"] = "Ollama inaccessible — lance ollama serve"
    except httpx.TimeoutException:
        result["message"] = "Ollama timeout au status — lance ollama serve"
    except Exception:
        result["message"] = "Ollama inaccessible — lance ollama serve"
    return result


async def chat_json(
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    timeout_seconds: float | int | None = None,
) -> dict[str, Any]:
    """Appel Ollama /api/chat format JSON."""
    config = load_llm_config()
    if not config.get("enabled"):
        raise RuntimeError("Ollama désactivé")

    base_url = str(config.get("base_url") or "http://localhost:11434").rstrip("/")
    timeout_val = timeout_seconds if timeout_seconds is not None else config.get("timeout_seconds")
    try:
        timeout_s = max(5, float(timeout_val or 25))
    except (TypeError, ValueError):
        timeout_s = 25.0

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            res = await client.post(
                f"{base_url}/api/chat",
                json={
                    "model": config.get("model") or "llama3.2",
                    "messages": messages,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": temperature},
                },
            )
    except httpx.ConnectError as exc:
        raise RuntimeError("Ollama inaccessible — lance ollama serve") from exc
    except httpx.TimeoutException as exc:
        raise RuntimeError(f"Ollama timeout ({timeout_s:.0f}s)") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Ollama réseau : {exc}") from exc

    if res.status_code >= 400:
        snippet = (res.text or "").strip().replace("\n", " ")[:180]
        raise RuntimeError(f"Ollama HTTP {res.status_code}{f' — {snippet}' if snippet else ''}")

    try:
        body = res.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError("Réponse Ollama non JSON") from exc

    raw = str((body.get("message") or {}).get("content") or "").strip()
    try:
        return _parse_json_loose(raw)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise RuntimeError("Réponse Ollama JSON invalide") from exc


def _parse_json_loose(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("JSON root must be an object")
    return parsed
