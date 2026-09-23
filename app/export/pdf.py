"""Export PDF A4 — exactement 1 page remplie (Pandoc HTML + WeasyPrint)."""

from __future__ import annotations

import io
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parent.parent.parent
STYLE_FILE = ROOT / "style.css"
PHOTO_PATH = "assets/photo-pro.jpg"

_SCALE_MIN = 0.52
_SCALE_MAX = 1.42
_BIN_ITERS = 8


@dataclass
class PdfExportResult:
    pdf_bytes: bytes
    page_count: int
    scale: float
    renders: int = 0
    elapsed_ms: float = 0.0


@dataclass(frozen=True)
class _Layout:
    scale: float
    gap_scale: float
    line_height: float


def count_pdf_pages(pdf_bytes: bytes) -> int:
    from pypdf import PdfReader

    return len(PdfReader(io.BytesIO(pdf_bytes)).pages)


def _normalize_photo_paths(markdown: str) -> str:
    return (
        markdown.replace("](lucas-schrever.jpg)", f"]({PHOTO_PATH})")
        .replace("](DSC02211.jpg)", f"]({PHOTO_PATH})")
        .replace("](DSC02211_square.jpg)", f"]({PHOTO_PATH})")
        .replace("](DSC02211_squaree.jpg)", f"]({PHOTO_PATH})")
        .replace("](assets/DSC02211_squaree.jpg)", f"]({PHOTO_PATH})")
    )


def _layout_from_scale(scale: float) -> _Layout:
    t = (scale - _SCALE_MIN) / (_SCALE_MAX - _SCALE_MIN)
    t = max(0.0, min(1.0, t))
    return _Layout(
        scale=scale,
        gap_scale=0.65 + 0.80 * t,
        line_height=1.12 + 0.28 * t,
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


def _wrap_utf8_html(fragment: str) -> str:
    """WeasyPrint lit en Latin-1 sans meta charset → mojibake sur accents."""
    return (
        "<!DOCTYPE html>\n"
        '<html lang="fr">\n'
        "<head>\n"
        '<meta charset="utf-8" />\n'
        "<title>CV</title>\n"
        "</head>\n"
        "<body>\n"
        f"{fragment}\n"
        "</body>\n"
        "</html>\n"
    )


def _pandoc_to_html(md_path: Path, html_path: Path, *, env: dict[str, str]) -> None:
    fragment_path = html_path.with_suffix(".frag.html")
    try:
        subprocess.run(
            [
                "pandoc",
                str(md_path),
                "-o",
                str(fragment_path),
                f"--resource-path={ROOT}",
            ],
            check=True,
            env=env,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        fragment = fragment_path.read_text(encoding="utf-8")
        html_path.write_text(_wrap_utf8_html(fragment), encoding="utf-8")
    finally:
        fragment_path.unlink(missing_ok=True)


def _weasyprint_pdf(
    html_path: Path,
    pdf_path: Path,
    override_css: Path,
    *,
    env: dict[str, str],
) -> bytes:
    subprocess.run(
        [
            "weasyprint",
            str(html_path),
            str(pdf_path),
            "--encoding=utf-8",
            f"--stylesheet={STYLE_FILE}",
            f"--stylesheet={override_css}",
        ],
        check=True,
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return pdf_path.read_bytes()


def _render_pages(
    html_path: Path,
    pdf_path: Path,
    *,
    env: dict[str, str],
    layout: _Layout,
) -> tuple[bytes, int]:
    override = _write_override_css(layout)
    try:
        pdf_bytes = _weasyprint_pdf(html_path, pdf_path, override, env=env)
        try:
            pages = count_pdf_pages(pdf_bytes)
        except Exception:
            pages = 1
        return pdf_bytes, pages
    finally:
        override.unlink(missing_ok=True)


def export_pdf_result(markdown: str) -> PdfExportResult:
    """UTF-8 HTML + dichotomie d'échelle : max scale qui tient en exactement 1 page."""
    if not STYLE_FILE.exists():
        raise HTTPException(503, "style.css introuvable à la racine du projet")

    photo = ROOT / Path(PHOTO_PATH)
    if not photo.exists():
        raise HTTPException(503, f"Photo introuvable : {photo}")

    env = os.environ.copy()
    env.setdefault("WEASYPRINT_DLL_DIRECTORIES", r"C:\msys64\mingw64\bin")
    markdown = _normalize_photo_paths(markdown)
    started = time.perf_counter()
    renders = 0

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8", dir=ROOT
    ) as md_file:
        md_file.write(markdown)
        md_path = Path(md_file.name)

    html_path = md_path.with_suffix(".html")
    pdf_path = md_path.with_suffix(".pdf")
    try:
        _pandoc_to_html(md_path, html_path, env=env)

        lo, hi = _SCALE_MIN, _SCALE_MAX
        best_bytes: bytes | None = None
        best_scale = _SCALE_MIN
        best_pages = 99

        for _ in range(_BIN_ITERS):
            mid = (lo + hi) / 2
            layout = _layout_from_scale(mid)
            pdf_bytes, pages = _render_pages(html_path, pdf_path, env=env, layout=layout)
            renders += 1
            if pages <= 1:
                lo = mid
                best_bytes, best_scale, best_pages = pdf_bytes, mid, pages
            else:
                hi = mid

        if best_bytes is None or best_pages > 1:
            layout = _layout_from_scale(_SCALE_MIN)
            pdf_bytes, pages = _render_pages(html_path, pdf_path, env=env, layout=layout)
            renders += 1
            best_bytes, best_scale, best_pages = pdf_bytes, _SCALE_MIN, pages

        elapsed_ms = (time.perf_counter() - started) * 1000
        return PdfExportResult(
            pdf_bytes=best_bytes,
            page_count=best_pages,
            scale=best_scale,
            renders=renders,
            elapsed_ms=elapsed_ms,
        )
    except FileNotFoundError as exc:
        missing = getattr(exc, "filename", None) or "pandoc/weasyprint"
        raise HTTPException(
            503,
            f"Outil manquant ({missing}). Installe Pandoc + WeasyPrint.",
        ) from None
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise HTTPException(503, f"Échec génération PDF : {detail}") from exc
    finally:
        md_path.unlink(missing_ok=True)
        html_path.unlink(missing_ok=True)
        pdf_path.unlink(missing_ok=True)


def export_pdf(markdown: str) -> bytes:
    return export_pdf_result(markdown).pdf_bytes
