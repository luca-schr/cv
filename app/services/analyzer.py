"""Analyse d'une fiche de poste."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.config import settings

ANALYSIS_FILE = settings.config_dir / "analysis.yaml"


@dataclass
class JobAnalysis:
    raw: str
    cleaned: str
    source: str
    title: str
    tags: set[str]


def load_analysis_config() -> dict:
    with ANALYSIS_FILE.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def clean_job_text(raw: str, config: dict) -> str:
    noise = tuple(config.get("noise_substrings", []))
    kept: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or len(stripped) < 3:
            continue
        lower = stripped.lower()
        if any(pattern in lower for pattern in noise):
            continue
        kept.append(stripped)
    return "\n".join(kept)


def extract_job_title(cleaned: str, config: dict, fallback: str) -> str:
    hints = tuple(config.get("title_hints", []))
    skip = tuple(config.get("title_skip", []))
    for line in cleaned.splitlines()[:30]:
        line = line.strip()
        if not line or len(line) > 90:
            continue
        lower = line.lower()
        if any(token in lower for token in skip):
            continue
        if any(hint in lower for hint in hints):
            return line
    first = next((line.strip() for line in cleaned.splitlines() if line.strip()), "")
    return first[:90] if first else fallback


def extract_tags(cleaned: str, config: dict) -> set[str]:
    normalized = cleaned.lower()
    tags: set[str] = set()
    for tag, aliases in config.get("tag_aliases", {}).items():
        for alias in aliases:
            alias = alias.lower()
            if len(alias) <= 3:
                if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", normalized):
                    tags.add(tag)
                    break
            elif alias in normalized:
                tags.add(tag)
                break
    return tags


def analyze_job(raw_text: str, source: str, title_fallback: str) -> JobAnalysis:
    config = load_analysis_config()
    cleaned = clean_job_text(raw_text, config)
    title = extract_job_title(cleaned, config, title_fallback)
    tags = extract_tags(cleaned, config)
    return JobAnalysis(raw=raw_text, cleaned=cleaned, source=source, title=title, tags=tags)
