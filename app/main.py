from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import ROOT, settings
from app.database import SessionLocal, init_db
from app.routers import export, generations, jobs, llm, profiles
from app.routers.profiles import sync_default_from_seed

CLIENT_DIST = ROOT / "client" / "dist"


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

app.mount("/assets", StaticFiles(directory=str(settings.assets_dir)), name="assets")

_ui_dir = CLIENT_DIST / "ui"
if _ui_dir.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_ui_dir)), name="client_ui")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(settings.assets_dir / "draw.png", media_type="image/png")


@app.get("/", include_in_schema=False)
def index():
    index_file = CLIENT_DIST / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return HTMLResponse(
        "<p>Frontend non compilé. En développement : <code>cd client && npm run dev</code> "
        "puis ouvre <a href='http://127.0.0.1:5173'>http://127.0.0.1:5173</a>. "
        "Sinon : <code>npm run build</code> dans <code>client/</code> et relance uvicorn.</p>",
        status_code=503,
    )


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
