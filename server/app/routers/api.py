from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

from app.database import get_db
from app.services.adapt import adapt_profile_to_job, repair_cv_markdown_headings
from app.services.filename import build_job_export_filename, extract_company
from app.services.match import (
    assess_skill_gap,
    build_match_context,
    find_best_profile,
    match_with_ollama,
    resolve_ollama_decision,
)
from app.services.ollama import check_ollama_status, llm_is_usable
from app.services.pdf import export_pdf

router = APIRouter()


class AnalyzeBody(BaseModel):
    job_text: str = ""
    english: bool = False
    profile_id: int | None = None


class ExportPdfBody(BaseModel):
    markdown: str = ""
    filename: str = "cv"


def map_profile_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "is_default": bool(row["is_default"]),
        "title": row.get("title"),
        "title_en": row.get("title_en"),
        "summary": row.get("summary"),
        "category": {
            "id": row.get("category_id"),
            "name": row.get("category_name"),
            "label_fr": row.get("category_label"),
        },
        "created_at": row.get("created_at"),
    }


def map_profile_detail(row: dict[str, Any], english: bool = False) -> dict[str, Any]:
    use_en = bool(english and row.get("markdown_en"))
    title = (
        row.get("title_en")
        if use_en and row.get("title_en")
        else row.get("title")
    )
    base = map_profile_summary(row)
    base.update(
        {
            "summary": (
                row.get("summary_en")
                if use_en and row.get("summary_en")
                else row.get("summary")
            ),
            "title": title,
            "markdown": row.get("markdown_en") if use_en else row.get("markdown"),
            "markdown_en": row.get("markdown_en"),
            "keywords": row.get("keywords"),
            "filename": build_job_export_filename(
                title or row.get("name"),
                None,
                english=english,
            ),
        }
    )
    return base


@router.get("/ping")
def ping() -> dict[str, bool]:
    return {"ok": True}


@router.get("/llm/status")
async def llm_status() -> dict[str, Any]:
    try:
        return await check_ollama_status()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, str(exc) or "Status Ollama impossible") from exc


@router.get("/categories")
def categories() -> dict[str, Any]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, label_fr FROM categories ORDER BY label_fr"
        ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.get("/profiles")
def list_profiles(
    q: str = Query(""),
    category: str = Query(""),
) -> dict[str, Any]:
    q = q.strip()
    category = category.strip()
    params: list[Any] = []
    sql = """
      SELECT p.id, p.name, p.is_default, p.title, p.title_en, p.summary, p.summary_en,
             p.keywords, p.created_at,
             c.id AS category_id, c.name AS category_name, c.label_fr AS category_label
      FROM profiles p
      JOIN categories c ON c.id = p.category_id
      WHERE 1=1
    """
    if q:
        sql += """ AND (
          p.name LIKE ? OR p.title LIKE ? OR p.summary LIKE ? OR p.keywords LIKE ?
          OR c.label_fr LIKE ? OR c.name LIKE ?
        )"""
        like = f"%{q}%"
        params.extend([like, like, like, like, like, like])
    if category:
        if category.isdigit():
            sql += " AND c.id = ?"
            params.append(int(category))
        else:
            sql += " AND c.name = ?"
            params.append(category)
    sql += " ORDER BY p.is_default DESC, p.name ASC"

    with get_db() as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    items = [map_profile_summary(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.get("/profiles/default")
def profile_default(english: bool = Query(False)) -> dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT p.*, c.id AS category_id, c.name AS category_name, c.label_fr AS category_label
            FROM profiles p JOIN categories c ON c.id = p.category_id
            WHERE p.is_default = 1 LIMIT 1
            """
        ).fetchone()
    if not row:
        raise HTTPException(404, "Aucun profil par défaut")
    return map_profile_detail(dict(row), english)


@router.get("/profiles/{profile_id}")
def profile_by_id(
    profile_id: int, english: bool = Query(False)
) -> dict[str, Any]:
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT p.*, c.id AS category_id, c.name AS category_name, c.label_fr AS category_label
            FROM profiles p JOIN categories c ON c.id = p.category_id
            WHERE p.id = ?
            """,
            (profile_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Profil introuvable")
    return map_profile_detail(dict(row), english)


@router.delete("/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: int) -> Response:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, is_default FROM profiles WHERE id = ?", (profile_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "Profil introuvable")
        if row["is_default"]:
            raise HTTPException(400, "Impossible de supprimer le profil par défaut.")
        conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    return Response(status_code=204)


@router.post("/analyze")
async def analyze(body: AnalyzeBody) -> dict[str, Any]:
    job_text = (body.job_text or "").strip()
    if len(job_text) < 10:
        raise HTTPException(400, "Colle une offre (min. 10 caractères).")

    with get_db() as conn:
        all_rows = [
            dict(r)
            for r in conn.execute(
                """
                SELECT p.*, c.id AS category_id, c.name AS category_name,
                       c.label_fr AS category_label
                FROM profiles p JOIN categories c ON c.id = p.category_id
                """
            ).fetchall()
        ]

    row = None
    matched_via = "selected"
    match_reason = None
    missing_skills: list[str] = []
    llm_status = await check_ollama_status()

    if body.profile_id and body.profile_id > 0:
        row = next((p for p in all_rows if p["id"] == body.profile_id), None)
        if not row:
            raise HTTPException(404, "Profil introuvable")
        missing_skills = assess_skill_gap(job_text, row).get("missing") or []
    else:
        context = build_match_context(job_text, all_rows)
        best: dict[str, Any]
        if context.get("skipOllama"):
            best = find_best_profile(job_text, all_rows)
        elif llm_is_usable(llm_status):
            try:
                decision = await match_with_ollama(
                    job_text, context.get("shortlist") or [], english=body.english
                )
                best = resolve_ollama_decision(decision, context, job_text)
            except Exception as exc:  # noqa: BLE001
                best = find_best_profile(job_text, all_rows)
                best["fallback"] = True
                best["source"] = "keywords"
                best["reason"] = f"Matching local — {exc}"
        else:
            best = find_best_profile(job_text, all_rows)
            if llm_status.get("enabled"):
                best["reason"] = llm_status.get("message")

        if not best.get("matched") or not best.get("profile"):
            return {
                "matched": False,
                "adapted": False,
                "message": best.get("message") or "Aucun profil assez proche",
                "reason": best.get("reason"),
                "source": best.get("source") or "keywords",
                "missing_skills": best.get("missing_skills") or [],
                "profile": None,
            }
        row = best["profile"]
        missing_skills = best.get("missing_skills") or []
        match_reason = best.get("reason")
        src = best.get("source")
        matched_via = "ollama" if src == "ollama" and not best.get("fallback") else "closest"

    try:
        base = map_profile_detail(row, body.english)
        adapted = await adapt_profile_to_job(
            base, job_text, english=body.english, llm_status=llm_status
        )
        company = adapted.get("company") or extract_company(job_text, None)
        filename = build_job_export_filename(
            adapted.get("title") or base.get("title") or base.get("name"),
            company,
            english=body.english,
        )
        profile = {
            **base,
            "title": adapted.get("title") or base.get("title"),
            "summary": adapted.get("summary") or base.get("summary"),
            "markdown": adapted["markdown"],
            "filename": filename,
            "company": company,
        }
        reason = adapted.get("reason")
        if match_reason and matched_via != "selected":
            reason = " · ".join(p for p in (match_reason, reason) if p)
        skipped = adapted.get("skipped_skills") or []
        return {
            "matched": True,
            "adapted": True,
            "matched_via": matched_via,
            "message": (
                f"{adapted.get('message')} (profil le plus proche)"
                if matched_via in {"closest", "ollama"}
                else adapted.get("message")
            ),
            "reason": reason,
            "source": adapted.get("source"),
            "fallback": bool(adapted.get("fallback")),
            "company": company,
            "added_skills": adapted.get("added_skills") or [],
            "missing_skills": list(dict.fromkeys([*(missing_skills or []), *skipped])),
            "profile": profile,
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, str(exc) or "Adaptation impossible") from exc


@router.post("/export/pdf")
def export_pdf_route(body: ExportPdfBody) -> Response:
    markdown = repair_cv_markdown_headings((body.markdown or "").strip())
    filename = (body.filename or "cv").strip() or "cv"
    if not markdown:
        raise HTTPException(400, "Markdown vide.")
    try:
        result = export_pdf(markdown, filename=filename)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, str(exc) or "Export PDF impossible") from exc

    return Response(
        content=result.pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
        },
    )
