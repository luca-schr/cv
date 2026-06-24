"""Orchestration génération CV."""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.services.analyzer import JobAnalysis, analyze_job
from app.services.llm import LLMAdaptation, adapt_with_llm
from app.services.renderer import build_markdown
from app.services.title_resolver import resolve_title


@dataclass
class GenerateResult:
    title: str
    markdown: str
    analysis: JobAnalysis
    llm_applied: bool
    warnings: list[str]


def generate_cv(cv_data: dict, job_text: str, *, use_llm: bool = True) -> GenerateResult:
    analysis = analyze_job(job_text, "text", cv_data["header"]["title_default"])
    llm_adaptation: LLMAdaptation | None = None
    if use_llm:
        llm_adaptation = adapt_with_llm(analysis, cv_data, force=True)
    llm_for_render = llm_adaptation if llm_adaptation and llm_adaptation.used_llm else None
    markdown = build_markdown(cv_data, analysis, llm_for_render)
    title = resolve_title(cv_data, analysis.tags, analysis.title)
    warnings = llm_adaptation.warnings if llm_adaptation else []
    return GenerateResult(
        title=title,
        markdown=markdown,
        analysis=analysis,
        llm_applied=bool(llm_for_render),
        warnings=warnings,
    )


def tags_to_json(tags: set[str]) -> str:
    return json.dumps(sorted(tags), ensure_ascii=False)


def tags_from_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    return json.loads(raw)
