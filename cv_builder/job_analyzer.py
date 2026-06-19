"""Analyse générique d'une fiche de poste."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_FILE = ROOT / "config" / "analysis.yaml"


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


def _alias_in_text(alias: str, normalized: str) -> bool:
    alias = alias.strip().lower()
    if len(alias) <= 3:
        return re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", normalized) is not None
    return alias in normalized


def clean_job_text(raw: str, config: dict) -> str:
    noise = tuple(config.get("noise_substrings", []))
    kept: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if any(pattern in lower for pattern in noise):
            continue
        if re.fullmatch(r"[\d.,/€$%\s]+", stripped):
            continue
        if len(stripped) < 3:
            continue
        kept.append(stripped)
    return "\n".join(kept)


def _line_frequency(raw: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in raw.splitlines():
        key = line.strip().lower()
        if key:
            counts[key] = counts.get(key, 0) + 1
    return counts


def extract_job_title(raw: str, cleaned: str, config: dict) -> str | None:
    hints = tuple(config.get("title_hints", []))
    skip = tuple(config.get("title_skip", []))
    frequencies = _line_frequency(raw)
    scored: list[tuple[float, str]] = []

    for index, line in enumerate(cleaned.splitlines()):
        line = line.strip()
        if not line or len(line) > 80:
            continue
        lower = line.lower()
        if any(token in lower for token in skip):
            continue
        if not any(hint in lower for hint in hints):
            continue

        score = frequencies.get(lower, 1) * 2.0
        if re.search(r"\bH/?F\b", line, re.IGNORECASE):
            score += 4
        if re.search(r"\(.*\)", line):
            score += 1
        score -= index * 0.02
        if 12 <= len(line) <= 70:
            score += 1
        scored.append((score, line))

    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def extract_job_tags(text: str, config: dict) -> set[str]:
    normalized = f" {text.lower()} "
    aliases_map: dict = config.get("tag_aliases", {})
    found: set[str] = set()
    for tag, aliases in aliases_map.items():
        for alias in aliases:
            if _alias_in_text(str(alias), normalized):
                found.add(tag)
                break
    return found


def resolve_title(
    extracted: str | None,
    job_tags: set[str],
    cleaned: str,
    default_title: str,
    config: dict,
) -> str:
    if extracted:
        return extracted

    for rule in config.get("title_fallbacks", []):
        required = set(rule.get("tags", []))
        if required and required.issubset(job_tags):
            return rule["title"]

    lower = cleaned.lower()
    for hint in config.get("title_hints", []):
        if hint in lower and len(hint) > 5:
            # Titre minimal dérivé du hint dominant dans le texte.
            return hint.capitalize()

    return default_title


def analyze_job(raw: str, source: str, default_title: str) -> JobAnalysis:
    config = load_analysis_config()
    cleaned = clean_job_text(raw, config)
    analysis_text = cleaned or raw
    tags = extract_job_tags(analysis_text, config)
    extracted = extract_job_title(raw, analysis_text, config)
    title = resolve_title(extracted, tags, analysis_text, default_title, config)
    return JobAnalysis(
        raw=raw,
        cleaned=analysis_text,
        source=source,
        title=title,
        tags=tags,
    )
