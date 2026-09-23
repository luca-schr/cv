from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from app import db as store

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:2b")


def _norm_lang(lang: str) -> str:
    return "en" if lang == "en" else "fr"


def _other_lang(lang: str) -> str:
    return "en" if lang == "fr" else "fr"


def _strip_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[: -3]
    return cleaned.strip()


def translate_markdown(markdown: str, source_lang: str, target_lang: str) -> str:
    source = "French" if source_lang == "fr" else "English"
    target = "English" if target_lang == "en" else "French"
    prompt = (
        f"Translate this CV markdown from {source} to {target}.\n"
        "Keep the same HTML, markdown, URLs, emails, names and structure.\n"
        "Translate visible headings and sentences only.\n"
        "Reply with the translated document only, no commentary.\n\n"
        f"{markdown.strip()}"
    )
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 4096},
    }
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return _strip_fences(str(body.get("response") or ""))


def apply_default(profile_id: str, lang: str, markdown: str) -> dict:
    lang = _norm_lang(lang)
    other = _other_lang(lang)
    translated = ""
    translated_ok = False
    error = None
    try:
        translated = translate_markdown(markdown, lang, other)
        translated_ok = bool(translated)
    except urllib.error.URLError as exc:
        error = f"Ollama injoignable ({exc})"
    except Exception as exc:
        error = str(exc)

    if not store.save_profile_pair(
        profile_id, lang, markdown, translated if translated_ok else None
    ):
        raise KeyError("Profil introuvable")

    return {
        "id": profile_id,
        "lang": lang,
        "other_lang": other,
        "ok": True,
        "translated": translated_ok,
        "error": error,
    }
