"""Scoring déterministe offre ↔ inventaire CV."""

from __future__ import annotations

from app.llm_models import JobBrief, MatchReport, SkillHit
from app.services.analyzer import JobAnalysis
from app.services.inventory import alias_groups, collect_blob, fold, term_in_inventory


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = fold(item)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def brief_from_heuristics(job: JobAnalysis) -> JobBrief:
    tags = sorted(job.tags)
    return JobBrief(
        title=job.title or "",
        company=job.company,
        keywords=tags,
        hard_skills=tags,
        missions=[],
        must_haves=tags[:8],
    )


def job_terms(job: JobAnalysis, brief: JobBrief) -> list[str]:
    return _unique(
        [
            *brief.hard_skills,
            *brief.must_haves,
            *brief.keywords,
            *sorted(job.tags),
        ]
    )


def score_match(cv_data: dict, job: JobAnalysis, brief: JobBrief) -> MatchReport:
    blob = collect_blob(cv_data)
    groups = alias_groups()
    terms = job_terms(job, brief)
    hits: list[SkillHit] = []
    matched: list[str] = []
    gaps: list[str] = []

    for term in terms:
        found = term_in_inventory(term, blob, groups)
        if found:
            matched.append(term)
            hits.append(SkillHit(term=term, status="matched", evidence=found))
        else:
            gaps.append(term)
            hits.append(SkillHit(term=term, status="gap"))

    total = len(terms) or 1
    score = len(matched) / total
    emphasize = matched[:12]
    vocabulary = _unique([*brief.hard_skills, *brief.keywords, *brief.missions])[:20]
    return MatchReport(
        score=score,
        matched=matched,
        emphasize=emphasize,
        gaps=gaps,
        vocabulary=vocabulary,
        hits=hits,
    )
