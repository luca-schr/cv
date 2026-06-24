"""Export PDF via Pandoc + WeasyPrint."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import HTTPException

from app.config import PHOTO_PATH, settings

STYLE_FILE = settings.style_file
ROOT = settings.config_dir.parent


def _normalize_photo_paths(markdown: str) -> str:
    """Compatibilité anciennes générations (photo à la racine)."""
    return markdown.replace("](lucas-schrever.jpg)", f"]({PHOTO_PATH})")


def export_pdf(markdown: str) -> bytes:
    if not STYLE_FILE.exists():
        raise HTTPException(503, "style.css introuvable à la racine du projet")

    photo = settings.assets_dir / "lucas-schrever.jpg"
    if not photo.exists():
        raise HTTPException(503, f"Photo introuvable : {photo}")

    env = os.environ.copy()
    env.setdefault("WEASYPRINT_DLL_DIRECTORIES", settings.weasyprint_dll)

    markdown = _normalize_photo_paths(markdown)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8", dir=ROOT
    ) as md_file:
        md_file.write(markdown)
        md_path = Path(md_file.name)

    pdf_path = md_path.with_suffix(".pdf")
    try:
        subprocess.run(
            [
                "pandoc",
                str(md_path),
                "-o",
                str(pdf_path),
                "--pdf-engine=weasyprint",
                f"--css={STYLE_FILE}",
                f"--resource-path={ROOT}",
            ],
            check=True,
            env=env,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        return pdf_path.read_bytes()
    except FileNotFoundError:
        raise HTTPException(
            503,
            "Pandoc non installé. Installe Pandoc + WeasyPrint pour exporter en PDF.",
        ) from None
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise HTTPException(503, f"Échec génération PDF : {detail}") from exc
    finally:
        md_path.unlink(missing_ok=True)
        pdf_path.unlink(missing_ok=True)
