from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = SERVER_ROOT.parent
PHOTO_PATH = "assets/lucas-schrever.jpg"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(REPO_ROOT / ".env"), extra="ignore")

    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'cv.db'}"
    config_dir: Path = SERVER_ROOT / "config"
    assets_dir: Path = SERVER_ROOT / "assets"
    style_file: Path = SERVER_ROOT / "style.css"
    weasyprint_dll: str = r"C:\msys64\mingw64\bin"
    client_dist: Path = REPO_ROOT / "client" / "dist"


settings = Settings()
