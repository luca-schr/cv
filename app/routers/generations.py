import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Generation, JobPosting, Profile
from app.schemas import GenerateRequest, GenerationRead, GenerationsPurgeRead
from app.services.analyzer import analyze_job
from app.services.generator import generate_cv, tags_from_json, tags_to_json
from app.services.pdf import export_pdf
from app.routers.profiles import get_default_profile

router = APIRouter(prefix="/generations", tags=["generations"])


def _to_read(gen: Generation, db: Session) -> GenerationRead:
    job = db.get(JobPosting, gen.job_id)
    return GenerationRead(
        id=gen.id,
        profile_id=gen.profile_id,
        job_id=gen.job_id,
        title=gen.title,
        markdown=gen.markdown,
        use_llm=gen.use_llm,
        llm_applied=gen.llm_applied,
        warnings=json.loads(gen.warnings or "[]"),
        detected_tags=tags_from_json(job.detected_tags if job else None),
        created_at=gen.created_at,
    )


@router.get("", response_model=list[GenerationRead])
def list_generations(db: Session = Depends(get_db)):
    gens = db.query(Generation).order_by(Generation.id.desc()).all()
    return [_to_read(g, db) for g in gens]


@router.delete("", response_model=GenerationsPurgeRead)
def purge_generations(db: Session = Depends(get_db)):
    """Supprime toutes les générations CV et les offres liées devenues orphelines."""
    job_ids = [row[0] for row in db.query(Generation.job_id).distinct().all()]
    deleted_generations = db.query(Generation).delete()
    deleted_jobs = 0
    if job_ids:
        deleted_jobs = (
            db.query(JobPosting)
            .filter(JobPosting.id.in_(job_ids))
            .filter(~JobPosting.generations.any())
            .delete(synchronize_session=False)
        )
    db.commit()
    return GenerationsPurgeRead(
        deleted_generations=deleted_generations,
        deleted_jobs=deleted_jobs,
    )


@router.get("/{generation_id}", response_model=GenerationRead)
def get_generation(generation_id: int, db: Session = Depends(get_db)):
    gen = db.get(Generation, generation_id)
    if not gen:
        raise HTTPException(404, "Génération introuvable")
    return _to_read(gen, db)


@router.delete("/{generation_id}", status_code=204)
def delete_generation(generation_id: int, db: Session = Depends(get_db)):
    gen = db.get(Generation, generation_id)
    if not gen:
        raise HTTPException(404, "Génération introuvable")
    db.delete(gen)
    db.commit()


@router.get("/{generation_id}/pdf")
def download_pdf(generation_id: int, db: Session = Depends(get_db)):
    gen = db.get(Generation, generation_id)
    if not gen:
        raise HTTPException(404, "Génération introuvable")
    pdf_bytes = export_pdf(gen.markdown)
    slug = gen.title.lower().replace(" ", "-")[:40] or "cv"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cv-{slug}.pdf"'},
    )


@router.post("", response_model=GenerationRead, status_code=201)
def create_generation(body: GenerateRequest, db: Session = Depends(get_db)):
    profile: Profile
    if body.profile_id:
        profile = db.get(Profile, body.profile_id)
        if not profile:
            raise HTTPException(404, "Profil introuvable")
    else:
        profile = get_default_profile(db)

    job: JobPosting | None = None
    job_text: str

    if body.job_id:
        job = db.get(JobPosting, body.job_id)
        if not job:
            raise HTTPException(404, "Offre introuvable")
        job_text = job.raw_text
    elif body.job_text:
        job_text = body.job_text
        cv_data_preview = json.loads(profile.data)
        analysis = analyze_job(job_text, "text", cv_data_preview["header"]["title_default"])
        job = JobPosting(
            raw_text=job_text,
            source="text",
            detected_title=analysis.title,
            detected_tags=tags_to_json(analysis.tags),
        )
        db.add(job)
        db.flush()
    else:
        raise HTTPException(400, "Fournir job_id ou job_text")

    cv_data = json.loads(profile.data)
    result = generate_cv(cv_data, job_text, use_llm=body.use_llm)

    if job and not job.detected_title:
        job.detected_title = result.analysis.title
        job.detected_tags = tags_to_json(result.analysis.tags)

    gen = Generation(
        profile_id=profile.id,
        job_id=job.id,
        title=result.title,
        markdown=result.markdown,
        use_llm=body.use_llm,
        llm_applied=result.llm_applied,
        warnings=json.dumps(result.warnings, ensure_ascii=False),
    )
    db.add(gen)
    db.commit()
    db.refresh(gen)
    return _to_read(gen, db)
