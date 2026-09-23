"""API CV : FastAPI par feature (selectprofile, applydefault, export)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.applydefault.router import router as applydefault_router
from app.db import init_db
from app.export.router import router as export_router
from app.selectprofile.router import router as selectprofile_router

ROOT = Path(__file__).resolve().parent.parent
CLIENT_DIST = ROOT / "client" / "dist"
ASSETS = ROOT / "assets"

app = FastAPI(title="CV", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(selectprofile_router)
app.include_router(applydefault_router)
app.include_router(export_router)

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


init_db()
