"""Orchestration génération CV."""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.services.analyzer import analyze_job
from app.services.llm import LLMAdaptation, adapt_with_llm, compress_cv_for_one_page
from app.services.pdf import export_pdf_result
from app.services.renderer import build_markdown
from app.services.sanitize import sanitize_cv_title

MAX_PAGE_ATTEMPTS = 4


@dataclass
class GenerateResult:
    title: str
    markdown: str
    analysis: object
    llm_applied: bool
    warnings: list[str]
    page_count: int | None = None


def generate_cv(
    cv_data: dict, job_text: str, *, use_llm: bool = True, english: bool = False
) -> GenerateResult:
    analysis = analyze_job(
        job_text, "text", cv_data["header"]["title_default"], use_llm=use_llm
    )
    llm_adaptation: LLMAdaptation | None = None
    if use_llm:
        llm_adaptation = adapt_with_llm(analysis, cv_data, force=True, english=english)
    llm_for_render = llm_adaptation if llm_adaptation and llm_adaptation.used_llm else None

    default_title = cv_data["header"]["title_default"]
    if llm_for_render and llm_for_render.title:
        title = sanitize_cv_title(llm_for_render.title)
    else:
        title = default_title

    warnings = list(llm_adaptation.warnings) if llm_adaptation else []
    if english and not llm_for_render:
        warnings.append("Traduction anglaise requiert le LLM.")

    markdown = ""
    page_count: int | None = None

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
    )


def tags_to_json(tags: set[str]) -> str:
    return json.dumps(sorted(tags), ensure_ascii=False)


def tags_from_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    return json.loads(raw)
