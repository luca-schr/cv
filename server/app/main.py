from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers.api import router as api_router

app = FastAPI(title="CV Generator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


app.include_router(api_router, prefix="/api")

client_dist = settings.client_dist
if client_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=client_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api"):
            return {"detail": "Not Found"}
        index = client_dist / "index.html"
        file_path = client_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        if index.is_file():
            return FileResponse(index)
        return {"detail": "Client dist manquant — npm run build dans client/"}
