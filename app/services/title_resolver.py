"""Résout un intitulé de poste canonique — jamais la copie littérale de l'offre."""

from __future__ import annotations


def resolve_title(cv_data: dict, job_tags: set[str], job_title_detected: str = "") -> str:
    header = cv_data.get("header", {})
    fallback = header.get("title_default", "Développeur")
    variants = cv_data.get("title_variants", [])
    if not variants:
        return fallback

    job_title_lower = job_title_detected.lower()
    best_title = fallback
    best_score = 0

    for variant in variants:
        score = 0
        match_tags = set(variant.get("match_tags", []))
        score += len(job_tags & match_tags) * 3
        for hint in variant.get("match_title", []):
            if hint.lower() in job_title_lower:
                score += 2
        if score > best_score:
            best_score = score
            best_title = variant["title"]

    return best_title if best_score > 0 else fallback
