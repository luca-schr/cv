import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import JobPosting
from app.schemas import JobCreate, JobRead
from app.services.analyzer import analyze_job
from app.services.generator import tags_from_json, tags_to_json
from app.routers.profiles import get_default_profile

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _to_read(job: JobPosting) -> JobRead:
    return JobRead(
        id=job.id,
        label=job.label,
        raw_text=job.raw_text,
        source=job.source,
        detected_title=job.detected_title,
        detected_tags=tags_from_json(job.detected_tags),
        created_at=job.created_at,
    )


@router.get("", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db)):
    return [_to_read(j) for j in db.query(JobPosting).order_by(JobPosting.id.desc()).all()]


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(JobPosting, job_id)
    if not job:
        raise HTTPException(404, "Offre introuvable")
    return _to_read(job)


@router.post("", response_model=JobRead, status_code=201)
def create_job(body: JobCreate, db: Session = Depends(get_db)):
    default = get_default_profile(db)
    cv_data = json.loads(default.data)
    analysis = analyze_job(body.raw_text, "text", cv_data["header"]["title_default"])
    job = JobPosting(
        label=body.label,
        raw_text=body.raw_text,
        source="text",
        detected_title=analysis.title,
        detected_tags=tags_to_json(analysis.tags),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _to_read(job)


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(JobPosting, job_id)
    if not job:
        raise HTTPException(404, "Offre introuvable")
    db.delete(job)
    db.commit()
