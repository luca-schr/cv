from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.config import settings
from app.database import init_db
from app.routers import export, generate, generations, llm

ASSETS = settings.assets_dir


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="CV Generator API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/ping")
def ping():
    return {"ok": True}


app.include_router(generate.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(generations.router, prefix="/api")
app.include_router(llm.router, prefix="/api")

dist = settings.client_dist
if dist.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(dist), html=True), name="spa")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(ASSETS / "draw.png", media_type="image/png")
