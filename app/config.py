from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
PHOTO_PATH = "assets/lucas-schrever.jpg"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = f"sqlite:///{ROOT / 'data' / 'cv.db'}"
    config_dir: Path = ROOT / "config"
    assets_dir: Path = ROOT / "assets"
    style_file: Path = ROOT / "style.css"
    weasyprint_dll: str = r"C:\msys64\mingw64\bin"


settings = Settings()
