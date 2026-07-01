from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import SessionLocal, init_db
from app.routers import export, generations, jobs, llm, profiles
from app.routers.profiles import sync_default_from_seed

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _load_index_html() -> str:
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")
    return html.replace(
        '<link rel="stylesheet" href="/static/app.css" />',
        f"<style>\n{css}\n</style>",
    )

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        sync_default_from_seed(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="CV Generator API",
    description="Backend FastAPI + SQLite pour générer des CV adaptés aux offres",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(export.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(generations.router, prefix="/api")
app.include_router(llm.router, prefix="/api")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/assets", StaticFiles(directory=str(settings.assets_dir)), name="assets")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(settings.assets_dir / "draw.png", media_type="image/png")


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(_load_index_html())


@app.get("/api")
def api_root():
    return {
        "message": "CV Generator API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
