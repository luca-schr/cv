"""API lite : profils JSON bilingues + aperçu markdown + export PDF 1 page."""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.export import PHOTO_PATH, export_pdf

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PROFILES_DIR = DATA / "profiles"
PERSON_FILE = DATA / "person.json"
CLIENT_DIST = ROOT / "client" / "dist"
ASSETS = ROOT / "assets"

Lang = str  # "fr" | "en"

SECTIONS = {
    "fr": {
        "profile": "Profil",
        "experience": "Expériences Professionnelles",
        "education": "Formations",
        "skills": "Compétences",
        "certs": "Certifications",
        "langs": "Langues",
    },
    "en": {
        "profile": "Summary",
        "experience": "Professional Experience",
        "education": "Education",
        "skills": "Skills",
        "certs": "Certifications",
        "langs": "Languages",
    },
}


class PdfRequest(BaseModel):
    markdown: str = Field(min_length=20)
    filename: str | None = Field(default=None, max_length=140)


def t(value: object, lang: Lang) -> str:
    """Lit un champ `{fr, en}` (FR par défaut si EN manquant)."""
    if isinstance(value, dict):
        return str(value.get(lang) or value.get("fr") or "").strip()
    return str(value or "").strip()


def load_person() -> dict:
    return json.loads(PERSON_FILE.read_text(encoding="utf-8"))


PROFILE_ORDER = (
    "fullstack",
    "chef-projet",
    "chef-projet-it",
    "product-owner",
    "wordpress",
    "cyber-grc",
)


def load_profiles() -> list[dict]:
    by_id: dict[str, dict] = {}
    for path in PROFILES_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("id", path.stem)
        by_id[data["id"]] = data
    ordered = [by_id[key] for key in PROFILE_ORDER if key in by_id]
    rest = [by_id[key] for key in sorted(by_id) if key not in PROFILE_ORDER]
    return ordered + rest


def get_profile(profile_id: str) -> dict:
    for profile in load_profiles():
        if profile.get("id") == profile_id:
            return profile
    raise HTTPException(404, "Profil introuvable")


def _description_lines(text: str) -> list[str]:
    lines = [ln.rstrip() for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return []
    bullets = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(("- ", "* ")):
            bullets.append(stripped[2:].strip())
        else:
            bullets.append(stripped)
    return bullets


def render_markdown(profile: dict, person: dict, lang: Lang) -> str:
    labels = SECTIONS["en" if lang == "en" else "fr"]
    title = t(profile.get("profile"), lang)
    location = t(person.get("location"), lang)
    email = person.get("email", "")
    phone = person.get("phone", "")
    photo = person.get("photo") or PHOTO_PATH

    contact = " · ".join(p for p in (location, phone) if p)
    if email:
        contact = f"{contact} · <a href=\"mailto:{email}\">{email}</a>" if contact else f'<a href="mailto:{email}">{email}</a>'
    links = " · ".join(
        f'<a href="{link["url"]}">{t(link.get("label"), lang)}</a>'
        for link in person.get("links") or []
        if link.get("url")
    )

    blocks = [
        '<div class="cv-page">',
        "<header class=\"cv-header\">",
        '<div class="cv-header-main">',
        f'<h1 class="cv-role">{title}</h1>',
        f'<p class="cv-name">{person.get("name", "")}</p>',
        f'<p class="cv-contact-primary">{contact}</p>',
    ]
    if links:
        blocks.append(f'<p class="cv-contact-links">{links}</p>')
    blocks += [
        "</div>",
        f'<img class="photo" src="{photo}" alt="" />',
        "</header>",
        "",
        f"## {labels['profile']}",
        "",
        t(profile.get("description"), lang),
        "",
        f"## {labels['experience']}",
        "",
    ]

    for exp in profile.get("experiences") or []:
        blocks.append(
            f"### {t(exp.get('title'), lang)} - {t(exp.get('company'), lang)} "
            f'<span class="cv-dates">{t(exp.get("time"), lang)}</span>'
        )
        blocks.append("")
        for line in _description_lines(t(exp.get("description"), lang)):
            blocks.append(f"- {line}")
        blocks.append("")

    blocks += [f"## {labels['education']}", ""]
    for formation in profile.get("formations") or []:
        blocks.append(
            f"### {t(formation.get('title'), lang)} - {t(formation.get('school'), lang)} "
            f'<span class="cv-dates">{t(formation.get("time"), lang)}</span>'
        )
        blocks.append("")
        desc = t(formation.get("description"), lang)
        if desc:
            blocks.append(f"- {desc}")
        blocks.append("")

    skills = profile.get("skills") or []
    if skills:
        blocks += [f"## {labels['skills']}", ""]
        for cat in skills:
            items = [t(item, lang) for item in cat.get("items") or []]
            items = [item for item in items if item]
            label = t(cat.get("label"), lang)
            if not label or not items:
                continue
            blocks += [f"### {label}", "", ", ".join(items), ""]

    certs = [t(c.get("title"), lang) for c in profile.get("certifications") or []]
    certs = [c for c in certs if c]
    if certs:
        blocks += [f"## {labels['certs']}", "", ", ".join(certs), ""]

    langs = profile.get("languages") or []
    if langs:
        blocks += [f"## {labels['langs']}", ""]
        for lang_item in langs:
            name = t(lang_item.get("title"), lang)
            level = t(lang_item.get("level"), lang)
            if name and level:
                blocks.append(f"- {name} : {level}")
            elif name:
                blocks.append(f"- {name}")
        blocks.append("")

    blocks += ["</div>", ""]
    return "\n".join(blocks)


def _safe_filename(raw: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", (raw or "cv").strip()).strip("-")
    return slug or "cv"


app = FastAPI(title="CV", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if ASSETS.is_dir():
    app.mount("/assets", StaticFiles(directory=str(ASSETS)), name="assets")

_ui_dir = CLIENT_DIST / "ui"
if _ui_dir.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_ui_dir)), name="client_ui")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(ASSETS / "draw.png", media_type="image/png")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/profiles")
def list_profiles():
    return [
        {"id": p["id"], "profile": p.get("profile", {})}
        for p in load_profiles()
    ]


@app.get("/api/profiles/{profile_id}")
def read_profile(profile_id: str, lang: Lang = "fr"):
    lang = "en" if lang == "en" else "fr"
    profile = get_profile(profile_id)
    person = load_person()
    return {
        "id": profile["id"],
        "lang": lang,
        "title": t(profile.get("profile"), lang),
        "profile": profile.get("profile", {}),
        "markdown": render_markdown(profile, person, lang),
    }


@app.post("/api/export/pdf")
def pdf_from_markdown(body: PdfRequest):
    pdf_bytes = export_pdf(body.markdown)
    slug = _safe_filename(body.filename or "cv")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{slug}.pdf"'},
    )


@app.get("/", include_in_schema=False)
def index():
    index_file = CLIENT_DIST / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return HTMLResponse(
        "<p>Frontend non compilé. <code>cd client && npm run build</code> "
        "puis relance uvicorn — ou <code>npm run dev</code> sur "
        "<a href='http://127.0.0.1:5173'>http://127.0.0.1:5173</a>.</p>",
        status_code=503,
    )
