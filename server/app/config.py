from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = SERVER_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8000
    database_path: Path = REPO_ROOT / "data" / "cv.db"
    style_file: Path = SERVER_ROOT / "style.css"
    assets_dir: Path = SERVER_ROOT / "assets"
    llm_config_path: Path = SERVER_ROOT / "config" / "llm.yaml"
    seed_data_path: Path = SERVER_ROOT / "app" / "seed_data.json"
    weasyprint_dll: str = r"C:\msys64\mingw64\bin"
    client_dist: Path = REPO_ROOT / "client" / "dist"


settings = Settings()
PHOTO_PATH = "assets/lucas-schrever.jpg"
