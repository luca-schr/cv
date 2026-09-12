"""Orchestration génération CV — pipeline extraction → match → réécriture."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.llm_models import JobBrief, MatchReport
from app.services.analyzer import JobAnalysis, analyze_job
from app.services.llm import LLMAdaptation, adapt_with_llm, apply_brief_to_analysis, compress_cv_for_one_page, extract_job_brief
from app.services.matching import brief_from_heuristics, score_match
from app.services.pdf import export_pdf_result
from app.services.renderer import build_markdown
from app.services.sanitize import sanitize_cv_title

MAX_PAGE_ATTEMPTS = 4


@dataclass
class GenerateResult:
    title: str
    markdown: str
    analysis: JobAnalysis
    llm_applied: bool
    warnings: list[str]
    page_count: int | None = None
    brief: JobBrief | None = None
    match: MatchReport | None = None
    pipeline: list[str] = field(default_factory=list)


def generate_cv(
    cv_data: dict, job_text: str, *, use_llm: bool = True, english: bool = False
) -> GenerateResult:
    pipeline = ["analyze"]
    analysis = analyze_job(
        job_text, "text", cv_data["header"]["title_default"], use_llm=False
    )

    if use_llm:
        pipeline.append("brief")
        brief = extract_job_brief(analysis)
    else:
        brief = brief_from_heuristics(analysis)
    analysis = apply_brief_to_analysis(analysis, brief)

    pipeline.append("match")
    match = score_match(cv_data, analysis, brief)

    llm_adaptation: LLMAdaptation | None = None
    if use_llm:
        pipeline.append("rewrite")
        llm_adaptation = adapt_with_llm(
            analysis,
            cv_data,
            brief=brief,
            match=match,
            force=True,
            english=english,
        )
    llm_for_render = llm_adaptation if llm_adaptation and llm_adaptation.used_llm else None

    default_title = cv_data["header"]["title_default"]
    if llm_for_render and llm_for_render.title:
        title = sanitize_cv_title(llm_for_render.title)
    elif brief.title:
        title = sanitize_cv_title(brief.title)
    else:
        title = default_title

    warnings = list(llm_adaptation.warnings) if llm_adaptation else []
    covered = len(match.matched)
    missing = len(match.gaps)
    warnings.insert(
        0,
        f"Match offre/CV : {int(match.score * 100)}% — {covered} compétence(s) couverte(s), "
        f"{missing} absente(s) du profil (non inventées).",
    )
    if english and not llm_for_render:
        warnings.append("Traduction anglaise requiert le LLM.")

    markdown = ""
    page_count: int | None = None
    pipeline.append("render")

    for attempt in range(MAX_PAGE_ATTEMPTS):
        markdown = build_markdown(
            cv_data, analysis, llm_for_render, title=title, english=english
        )
        pdf_result = export_pdf_result(markdown)
        page_count = pdf_result.page_count

        if page_count <= 1:
            break

        if not use_llm or not llm_for_render:
            warnings.append(
                "Le CV dépasse 1 page A4 — active le LLM pour compresser le contenu automatiquement."
            )
            break

        compressed = compress_cv_for_one_page(
            cv_data,
            llm_for_render,
            english=english,
            attempt=attempt + 1,
        )
        if not compressed:
            warnings.append("Compression LLM indisponible — PDF peut dépasser 1 page.")
            break

        llm_for_render = compressed
        warnings.append(f"Le LLM a raccourci le contenu (tentative {attempt + 1}) pour tenir sur 1 page.")

    return GenerateResult(
        title=title,
        markdown=markdown,
        analysis=analysis,
        llm_applied=bool(llm_for_render),
        warnings=warnings,
        page_count=page_count,
        brief=brief,
        match=match,
        pipeline=pipeline,
    )


def tags_to_json(tags: set[str]) -> str:
    return json.dumps(sorted(tags), ensure_ascii=False)


def tags_from_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    return json.loads(raw)
