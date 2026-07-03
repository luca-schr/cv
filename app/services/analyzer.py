"""Analyse d'une fiche de poste."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.config import settings
from app.services.sanitize import sanitize_cv_title

ANALYSIS_FILE = settings.config_dir / "analysis.yaml"


@dataclass
class JobAnalysis:
    raw: str
    cleaned: str
    source: str
    company: str | None
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
            return sanitize_cv_title(line)
    first = next((line.strip() for line in cleaned.splitlines() if line.strip()), "")
    return sanitize_cv_title(first[:90] if first else fallback)


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


def _looks_like_job_title(line: str, config: dict) -> bool:
    """Exclut les intitulés de poste pris à tort pour une entreprise."""
    lower = line.lower()
    for hint in config.get("title_hints", []):
        if hint in lower:
            return True
    if re.search(r"\bH\s*/\s*F\b", line, flags=re.IGNORECASE):
        return True
    if re.search(r"\b(junior|senior|stagiaire|alternant|confirm[eé]|lead|n\+[1-9])\b", lower):
        return True
    if re.search(r"\b(java|react|angular|vue|node\.?js|php|c#|\.net|python)\s*/", lower):
        return True
    if re.search(r"/\s*(java|react|angular|vue|node|php|javascript)\b", lower):
        return True
    return False


def extract_company(cleaned: str, config: dict | None = None) -> str | None:
    """
    Heuristique pour nom d'entreprise (nommage de fichier / historique).
    Priorité : libellés explicites (Employeur, Entreprise…) > lignes utiles > URL métier.
    """
    cfg = config or load_analysis_config()
    text = cleaned.strip()
    if not text:
        return None

    def accept(name: str | None) -> str | None:
        if not name or _looks_like_job_title(name, cfg):
            return None
        return name

    def normalize(raw: str) -> str | None:
        company = re.sub(r"\s{2,}", " ", raw.strip())
        company = company.strip(" ,.;:-–—*[]{}")
        if len(company) < 2:
            return None
        acronym = re.search(r"\(([A-Z][A-Z0-9]{1,15})\)\s*$", company)
        if acronym:
            return acronym.group(1)
        short = re.search(r"\(([A-Za-z][\w&.\- ]{2,25})\)\s*$", company)
        if short and len(company) > 45:
            return short.group(1).strip()
        return company[:80]

    labeled_patterns = [
        r"(?:employeur|entreprise|soci[eé]t[eé]|recruteur|company)\s*:\s*(.+?)(?:\n|$)",
        r"\bbienvenue\s+chez\s+(.+?)(?:\n|$)",
        r"\bchez\s+([A-ZÀ-Ÿ][\w&.\- ''\u2019]{1,80})",
        r"\b([A-ZÀ-Ÿ][\w&.\-]{1,50})\s+est\s+une?\b",
    ]
    for pattern in labeled_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if not match:
            continue
        company = normalize(match.group(1))
        if company:
            return accept(company)

    skip_line_substrings = (
        "http",
        "source url",
        "title:",
        "cookie",
        "menu",
        "accueil",
        "offres d'emploi",
        "république",
        "française",
        "partager",
        "télécharger",
        "candidature",
        "postuler",
        "détails de l'emploi",
        "correspondance entre",
        "employeur :",
    )
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for candidate in lines[1:20]:
        candidate = candidate.strip(" ,.;:-–—()[]{}*")
        lower = candidate.lower()
        if len(candidate) < 2 or len(candidate) > 60:
            continue
        if any(token in lower for token in skip_line_substrings):
            continue
        if re.search(r"\d{4,}", candidate):
            continue
        if re.search(
            r"\b(paris|lyon|marseille|lille|nantes|toulouse|bordeaux|rennes|ivry)\b", lower
        ):
            continue
        if re.search(r"\b(cdi|cdd|stage|alternance|freelance|ind[eé]pendant)\b", lower):
            continue
        if _looks_like_job_title(candidate, cfg):
            continue
        company = normalize(candidate)
        if company:
            return accept(company)

    url = next((m.group(0) for m in re.finditer(r"https?://[^\s)]+", text)), None)
    if url:
        lower = url.lower()
        match = re.search(r"/companies/([^/]+)/?", lower)
        if match:
            return accept(normalize(match.group(1).replace("-", " ").title()))
        match = re.search(r"/company/([^/?#]+)/?", lower)
        if match:
            return accept(normalize(match.group(1).replace("-", " ").title()))
        host = re.sub(r"^https?://", "", lower).split("/")[0].split(":")[0]
        parts = host.replace("www.", "").split(".")
        generic = {
            "gouv", "fr", "com", "net", "org", "co", "uk", "io",
            "choisirleservicepublic", "indeed", "linkedin", "welcometothejungle",
            "wttj", "glassdoor", "monster", "apec",
        }
        if len(parts) >= 2:
            candidate = parts[-2]
            if candidate not in generic:
                return accept(normalize(candidate.replace("-", " ").title()))

    return None


def analyze_job(
    raw_text: str, source: str, title_fallback: str, *, use_llm: bool = False
) -> JobAnalysis:
    config = load_analysis_config()
    cleaned = clean_job_text(raw_text, config)
    company = extract_company(cleaned, config)
    title = extract_job_title(cleaned, config, title_fallback)

    if use_llm:
        from app.services.llm import extract_job_meta_with_llm

        meta = extract_job_meta_with_llm(cleaned)
        if meta and meta.used_llm:
            if meta.title:
                title = meta.title
            if meta.company and not _looks_like_job_title(meta.company, config):
                company = meta.company

    tags = extract_tags(cleaned, config)
    return JobAnalysis(raw=raw_text, cleaned=cleaned, source=source, company=company, title=title, tags=tags)
