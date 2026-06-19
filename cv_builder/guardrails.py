"""Garde-fous factuels pour la réécriture LLM."""

from __future__ import annotations

import re
from urllib.parse import urlparse

MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
TECH_TOKEN = re.compile(
    r"\b(?:"
    r"React|Next\.js|NestJS|\.NET|TypeScript|JavaScript|WordPress|Vue\.js|"
    r"GraphQL|PostgreSQL|Docker|Git|PHP|SEO|Agile|Material UI|TanStack Query|"
    r"Tailwind CSS|Sass|MySQL|MongoDB|GitHub Actions|Figma|API REST|UX/UI|"
    r"MUI|Node\.js|Express|Strapi|Sylius|Drupal|CMS"
    r")\b",
    re.IGNORECASE,
)


def extract_urls(text: str) -> set[str]:
    urls: set[str] = set()
    for match in MARKDOWN_LINK.finditer(text):
        urls.add(match.group(2).strip())
    for token in re.findall(r"https?://\S+", text):
        urls.add(token.rstrip(".,;)"))
    return urls


def build_allowed_vocabulary(cv_data: dict) -> set[str]:
    vocab: set[str] = set()

    for block in cv_data.get("profil", {}).get("keywords", []):
        vocab.add(block["term"].lower())

    for category in cv_data.get("competences", []):
        for item in category.get("items", []):
            vocab.add(item["term"].lower())

    for exp in cv_data.get("experiences", []):
        vocab.add(exp["company"].lower())
        for bullet in exp.get("bullets", []):
            text = bullet["text"].lower()
            vocab.update(word for word in re.findall(r"[a-z0-9.#+]+", text) if len(word) > 2)

    for formation in cv_data.get("formations", []):
        vocab.add(formation["title"].lower())
        vocab.add(formation["school"].lower())

    vocab.update(
        {
            "rest", "api", "hooks", "react", "wordpress", "fullstack", "full stack",
            "front-end", "back-end", "frontend", "backend", "agile", "scrum",
            "marketing", "landing", "pages", "sites", "web", "digital", "extranet",
            "maintenance", "extensions", "optimisation", "audits", "performance",
            "indicateurs", "engagement", "recette", "spécifications", "supervision",
        }
    )
    return vocab


def validate_profil(profil: str, allowed: set[str], max_chars: int = 520) -> bool:
    if not profil or len(profil) > max_chars:
        return False
    for token in TECH_TOKEN.findall(profil):
        if token.lower() not in allowed:
            return False
    return True


def validate_bullet_rewrite(rewritten: str, original: str, allowed: set[str]) -> bool:
    if not rewritten or len(rewritten) > max(len(original) * 1.6, 400):
        return False

    original_urls = extract_urls(original)
    if original_urls and not original_urls.issubset(extract_urls(rewritten)):
        return False

    for token in TECH_TOKEN.findall(rewritten):
        if token.lower() not in allowed:
            return False

    return True


def validate_title(title: str, max_len: int = 90) -> bool:
    return bool(title and 5 <= len(title) <= max_len)
