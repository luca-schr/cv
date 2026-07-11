from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Generation
from app.schemas import GenerationDetail, GenerationSummary

router = APIRouter(prefix="/generations", tags=["generations"])


@router.get("", response_model=list[GenerationSummary])
def list_generations(db: Session = Depends(get_db)):
    rows = db.query(Generation).order_by(Generation.created_at.desc()).limit(50).all()
    return [
        GenerationSummary(
            id=g.id,
            title=g.title,
            company=g.company,
            version=g.version or 1,
            filename=g.export_filename or "cv",
            created_at=g.created_at,
        )
        for g in rows
    ]


@router.get("/{generation_id}", response_model=GenerationDetail)
def get_generation(generation_id: int, db: Session = Depends(get_db)):
    gen = db.get(Generation, generation_id)
    if not gen:
        raise HTTPException(404, "Génération introuvable")
    return GenerationDetail(
        id=gen.id,
        title=gen.title,
        company=gen.company,
        version=gen.version or 1,
        filename=gen.export_filename or "cv",
        created_at=gen.created_at,
        markdown=gen.markdown,
        job_text=gen.job_text,
    )
