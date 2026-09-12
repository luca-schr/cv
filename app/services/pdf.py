"""Export PDF via Pandoc + WeasyPrint — remplissage A4 une page."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException

from app.config import PHOTO_PATH, settings
from app.services.pdf_fit import count_pdf_pages

STYLE_FILE = settings.style_file
ROOT = settings.config_dir.parent


@dataclass
class PdfExportResult:
    pdf_bytes: bytes
    page_count: int
    scale: float


@dataclass(frozen=True)
class _Layout:
    scale: float
    gap_scale: float
    line_height: float


def _normalize_photo_paths(markdown: str) -> str:
    return (
        markdown.replace("](lucas-schrever.jpg)", f"]({PHOTO_PATH})")
        .replace("](DSC02211.jpg)", f"]({PHOTO_PATH})")
        .replace("](DSC02211_square.jpg)", f"]({PHOTO_PATH})")
    )


def _write_override_css(layout: _Layout) -> Path:
    handle = tempfile.NamedTemporaryFile(
        mode="w", suffix=".css", delete=False, encoding="utf-8"
    )
    handle.write(
        ":root {\n"
        f"  --cv-scale: {layout.scale:.4f};\n"
        f"  --cv-gap-scale: {layout.gap_scale:.4f};\n"
        f"  --cv-line-height: {layout.line_height:.3f};\n"
        "}\n"
    )
    handle.close()
    return Path(handle.name)


def _run_pandoc(
    md_path: Path,
    pdf_path: Path,
    override_css: Path,
    *,
    env: dict[str, str],
) -> None:
    subprocess.run(
        [
            "pandoc",
            str(md_path),
            "-o",
            str(pdf_path),
            "--pdf-engine=weasyprint",
            f"--css={STYLE_FILE.resolve().as_uri()}",
            f"--css={override_css.resolve().as_uri()}",
            f"--resource-path={ROOT}",
        ],
        check=True,
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def _render_pdf(
    md_path: Path,
    pdf_path: Path,
    *,
    env: dict[str, str],
    layout: _Layout,
) -> tuple[bytes, Path]:
    override = _write_override_css(layout)
    try:
        _run_pandoc(md_path, pdf_path, override, env=env)
        return pdf_path.read_bytes(), override
    except Exception:
        override.unlink(missing_ok=True)
        raise


def _count_safe(pdf_bytes: bytes) -> int:
    try:
        return count_pdf_pages(pdf_bytes)
    except Exception:
        return 1


def _fits_one_page(md_path: Path, pdf_path: Path, *, env: dict[str, str], layout: _Layout) -> bool:
    pdf_bytes, override = _render_pdf(md_path, pdf_path, env=env, layout=layout)
    try:
        return _count_safe(pdf_bytes) <= 1
    finally:
        override.unlink(missing_ok=True)


def _render_best(
    md_path: Path,
    pdf_path: Path,
    *,
    env: dict[str, str],
    layout: _Layout,
) -> PdfExportResult:
    pdf_bytes, override = _render_pdf(md_path, pdf_path, env=env, layout=layout)
    try:
        return PdfExportResult(
            pdf_bytes=pdf_bytes,
            page_count=_count_safe(pdf_bytes),
            scale=layout.scale,
        )
    finally:
        override.unlink(missing_ok=True)


def _shrink_layout(layout: _Layout) -> _Layout:
    return _Layout(
        scale=max(0.52, layout.scale - 0.04),
        gap_scale=max(0.65, layout.gap_scale - 0.05),
        line_height=max(1.12, layout.line_height - 0.02),
    )


def _grow_layout(layout: _Layout, factor: float) -> _Layout:
    return _Layout(
        scale=layout.scale * factor,
        gap_scale=min(1.45, layout.gap_scale * factor),
        line_height=min(1.42, layout.line_height + (factor - 1) * 0.12),
    )


def _find_fitting_layout(md_path: Path, pdf_path: Path, *, env: dict[str, str]) -> _Layout:
    layout = _Layout(scale=1.0, gap_scale=1.0, line_height=1.22)
    for _ in range(12):
        if _fits_one_page(md_path, pdf_path, env=env, layout=layout):
            return layout
        layout = _shrink_layout(layout)
    return layout


def _maximize_fill(
    md_path: Path,
    pdf_path: Path,
    *,
    env: dict[str, str],
    base: _Layout,
) -> PdfExportResult:
    """Agrandit au maximum (échelle + espacements) tout en restant sur 1 page."""
    best = _render_best(md_path, pdf_path, env=env, layout=base)
    if best.page_count > 1:
        return best

    current = base
    factor = 1.06
    while factor <= 1.42:
        candidate = _grow_layout(current, factor)
        if not _fits_one_page(md_path, pdf_path, env=env, layout=candidate):
            break
        current = candidate
        best = _render_best(md_path, pdf_path, env=env, layout=current)
        factor = round(factor + 0.03, 3)

    # Affinage binaire sur l'échelle
    lo, hi = current.scale, current.scale * 1.18
    gap = current.gap_scale
    lh = current.line_height
    for _ in range(8):
        mid = (lo + hi) / 2
        candidate = _Layout(scale=mid, gap_scale=gap * (mid / current.scale), line_height=lh)
        if _fits_one_page(md_path, pdf_path, env=env, layout=candidate):
            lo = mid
            best = _render_best(md_path, pdf_path, env=env, layout=candidate)
        else:
            hi = mid

    return best


def _optimize_layout(md_path: Path, pdf_path: Path, *, env: dict[str, str]) -> PdfExportResult:
    fitting = _find_fitting_layout(md_path, pdf_path, env=env)
    return _maximize_fill(md_path, pdf_path, env=env, base=fitting)


def export_pdf_result(markdown: str) -> PdfExportResult:
    if not STYLE_FILE.exists():
        raise HTTPException(503, "style.css introuvable à la racine du projet")

    photo = ROOT / Path(PHOTO_PATH)
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
        return _optimize_layout(md_path, pdf_path, env=env)
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


def export_pdf(markdown: str) -> bytes:
    return export_pdf_result(markdown).pdf_bytes
