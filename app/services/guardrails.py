"""Garde-fous factuels pour la réécriture LLM."""

from __future__ import annotations

import re

MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
TECH_TOKEN = re.compile(
    r"\b(?:React|Next\.js|NestJS|\.NET|TypeScript|JavaScript|WordPress|Vue\.js|"
    r"GraphQL|PostgreSQL|Docker|Git|PHP|SEO|Agile|Material UI|TanStack Query|"
    r"Tailwind CSS|Sass|MySQL|MongoDB|GitHub Actions|Figma|API REST|UX/UI|MUI|Node\.js|C#)\b",
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
            vocab.update(
                word for word in re.findall(r"[a-z0-9.#+]+", bullet["text"].lower()) if len(word) > 2
            )
    vocab.update(
        {
            "rest", "api", "react", "wordpress", "fullstack", "frontend", "backend",
            "agile", "web", "maintenance", "optimisation", "seo", "performance",
        }
    )
    return vocab


def validate_profil(profil: str, allowed: set[str], max_chars: int = 520) -> bool:
    if not profil or len(profil) > max_chars:
        return False
    return all(token.lower() in allowed for token in TECH_TOKEN.findall(profil))


def validate_bullet_rewrite(rewritten: str, original: str, allowed: set[str]) -> bool:
    if not rewritten or len(rewritten) > max(len(original) * 1.6, 400):
        return False
    original_urls = extract_urls(original)
    if original_urls and not original_urls.issubset(extract_urls(rewritten)):
        return False
    return all(token.lower() in allowed for token in TECH_TOKEN.findall(rewritten))


def validate_title(title: str, max_len: int = 90) -> bool:
    return bool(title and 5 <= len(title) <= max_len)
