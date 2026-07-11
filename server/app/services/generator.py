"""Orchestration génération CV."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.bootstrap import persist_job_skills, profile_data, seed_profile_if_needed, skills_snapshot
from app.database import SessionLocal
from app.models import Generation, Profile
from app.services.filename import build_export_filename, next_generation_version
from app.services.llm import CvAdaptation, adapt_cv, analyze_job, compress_cv
from app.services.pdf import export_pdf_result
from app.services.progress import NO_PROGRESS, ProgressFn
from app.services.renderer import build_markdown
from app.services.sanitize import sanitize_cv_title
from app.services.subskills import (
    build_skill_groups_for_cv,
    enrich_skill_groups,
    extract_title_technologies,
    format_subskill_hints,
    merge_skill_groups,
    select_relevant_subskills,
)

MAX_PAGE_ATTEMPTS = 4


@contextmanager
def _short_db():
    """Session courte — ne pas garder SQLite ouvert pendant Ollama/PDF."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _adaptation_quality_warnings(adaptation: CvAdaptation, data: dict) -> list[str]:
    warnings: list[str] = []
    if not adaptation.profil or len(adaptation.profil.strip()) < 40:
        warnings.append("Profil non adapté ou trop court.")
    if not adaptation.bullets:
        warnings.append("Expériences non reformulées (bullets absents).")
        return warnings

    changed = 0
    for exp in data.get("experiences", []):
        eid = exp.get("id")
        if eid not in adaptation.bullets:
            continue
        orig = [
            b if isinstance(b, str) else b.get("text", "")
            for b in exp.get("bullets", [])
        ]
        if adaptation.bullets[eid] != orig:
            changed += 1
    if changed == 0:
        warnings.append("Les bullets semblent identiques au corpus — adaptation faible.")
    return warnings


@dataclass
class GenerateResult:
    generation_id: int
    title: str
    company: str | None
    markdown: str
    warnings: list[str]
    page_count: int | None
    version: int
    filename: str


def generate_cv(
    *,
    job_text: str,
    english: bool = False,
    temperature: float = 0.45,
    progress: ProgressFn = NO_PROGRESS,
) -> GenerateResult:
    warnings: list[str] = []

    progress("profile", "Chargement du profil…", 5)
    with _short_db() as db:
        profile = seed_profile_if_needed(db)
        profile_id = profile.id
        data = profile_data(profile)

    progress("analyze", "Analyse de l'offre (Ollama)…", 12)
    try:
        analysis = analyze_job(job_text, temperature=temperature)
    except Exception as exc:
        raise RuntimeError(f"Analyse Ollama échouée : {exc}") from exc
    progress("analyze", f"Offre analysée — {analysis.job_title}", 22)

    snapshot: list[dict]
    if analysis.categories:
        progress("skills", "Enregistrement des compétences de l'offre…", 28)
        with _short_db() as db:
            profile = db.get(Profile, profile_id)
            persist_job_skills(db, profile, analysis.categories)
            skill_count = sum(len(c.get("skills", [])) for c in analysis.categories)
            snapshot = skills_snapshot(db, profile)
        warnings.append(f"{skill_count} skill(s) offre persistée(s).")
        progress("skills", f"{skill_count} compétence(s) enregistrée(s)", 32)
    else:
        with _short_db() as db:
            profile = db.get(Profile, profile_id)
            snapshot = skills_snapshot(db, profile)

    title_technologies = extract_title_technologies(analysis.job_title, snapshot)
    relevant_subskills = select_relevant_subskills(
        snapshot,
        job_analysis=analysis,
        job_text=job_text,
    )
    built_skill_groups = build_skill_groups_for_cv(
        snapshot,
        relevant_subskills=relevant_subskills,
        title_technologies=title_technologies,
        job_analysis=analysis,
        job_text=job_text,
    )
    subskill_hints = format_subskill_hints(relevant_subskills)
    if title_technologies:
        progress("adapt", f"Titre — technos : {', '.join(title_technologies)}", 34)
    if relevant_subskills:
        progress(
            "adapt",
            f"Adaptation CV — {len(relevant_subskills)} subskill(s) ciblée(s)…",
            36,
        )

    progress("adapt", "Adaptation du CV (Ollama)…", 38)
    try:
        adaptation = adapt_cv(
            profile_data=data,
            skills_snapshot=snapshot,
            job_analysis=analysis,
            job_text=job_text,
            relevant_subskills=relevant_subskills,
            subskill_hints=subskill_hints,
            title_technologies=title_technologies,
            temperature=temperature,
            english=english,
        )
        adaptation.skill_groups = merge_skill_groups(
            adaptation.skill_groups,
            built_skill_groups,
        )
        adaptation.skill_groups = enrich_skill_groups(
            adaptation.skill_groups,
            relevant_subskills,
        )
    except Exception as exc:
        raise RuntimeError(f"Adaptation Ollama échouée : {exc}") from exc
    warnings.extend(_adaptation_quality_warnings(adaptation, data))
    if title_technologies:
        warnings.append(f"Titre : {', '.join(title_technologies)} intégré(s) aux compétences.")
    if relevant_subskills:
        warnings.append(f"{len(relevant_subskills)} subskill(s) affichée(s) dans le CV.")
    progress("adapt", "Profil et expériences adaptés", 52)

    title = adaptation.title or analysis.job_title or data["header"]["title_default"]
    title = sanitize_cv_title(title)
    company = analysis.company

    markdown = ""
    page_count: int | None = None
    current = adaptation

    for attempt in range(MAX_PAGE_ATTEMPTS):
        progress("markdown", "Composition du markdown…", 58)
        markdown = build_markdown(data, title=title, adaptation=current, english=english)
        progress(
            "pdf",
            f"Vérification PDF A4 — tentative {attempt + 1}/{MAX_PAGE_ATTEMPTS}…",
            62 + attempt * 6,
        )
        pdf_result = export_pdf_result(
            markdown,
            progress=lambda step, label, pct: progress(
                "pdf",
                label,
                62 + attempt * 6 + (pct or 0) // 25,
            ),
        )
        page_count = pdf_result.page_count
        if page_count <= 1:
            progress("pdf", f"PDF validé — {page_count} page", 78)
            break
        try:
            progress(
                "compress",
                f"Compression Ollama — tentative {attempt + 1}…",
                80 + attempt * 3,
            )
            compressed = compress_cv(
                profile_data=data,
                current=current,
                attempt=attempt + 1,
                temperature=min(temperature, 0.3),
                english=english,
            )
            current = compressed
            warnings.append(f"Compression Ollama (tentative {attempt + 1}).")
            progress("compress", f"Texte raccourci (tentative {attempt + 1})", 84)
        except Exception as exc:
            warnings.append(f"Compression impossible : {exc}")
            break

    if page_count and page_count > 1:
        warnings.append("Le PDF peut dépasser 1 page.")

    progress("save", "Sauvegarde de la génération…", 94)
    with _short_db() as db:
        version = next_generation_version(db, profile_id=profile_id, title=title, company=company)
        filename = build_export_filename(title, company, version=version)
        gen = Generation(
            profile_id=profile_id,
            title=title,
            company=company,
            version=version,
            export_filename=filename,
            markdown=markdown,
            job_text=job_text,
        )
        db.add(gen)
        db.flush()
        gen_id = gen.id

    progress("save", f"Enregistré — {filename}", 100)

    return GenerateResult(
        generation_id=gen_id,
        title=title,
        company=company,
        markdown=markdown,
        warnings=warnings,
        page_count=page_count,
        version=version,
        filename=filename,
    )
