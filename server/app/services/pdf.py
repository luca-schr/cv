"""Export PDF via Pandoc + WeasyPrint — fit A4 une page (proportions CSS)."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException

from app.config import PHOTO_PATH, settings
from app.services.pdf_fit import count_pdf_pages

STYLE_FILE = settings.style_file
ROOT = settings.style_file.parent  # server/


@dataclass
class PdfExportResult:
    pdf_bytes: bytes
    page_count: int
    scale: float
    filename: str


@dataclass(frozen=True)
class _Layout:
    scale: float
    gap_scale: float
    line_height: float


def _normalize_photo_paths(markdown: str) -> str:
    md = str(markdown or "")
    md = md.replace("](lucas-schrever.jpg)", f"]({PHOTO_PATH})")
    md = md.replace("](assets/lucas-schrever.jpg)", f"]({PHOTO_PATH})")
    md = re.sub(
        r'src=["\']lucas-schrever\.jpg["\']',
        f'src="{PHOTO_PATH}"',
        md,
    )
    md = re.sub(
        r'src=["\']assets/lucas-schrever\.jpg["\']',
        f'src="{PHOTO_PATH}"',
        md,
    )
    return md


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
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def _count_safe(pdf_bytes: bytes) -> int:
    try:
        return count_pdf_pages(pdf_bytes)
    except Exception:
        return 1


def _render(
    md_path: Path,
    pdf_path: Path,
    *,
    env: dict[str, str],
    layout: _Layout,
) -> PdfExportResult:
    override = _write_override_css(layout)
    try:
        _run_pandoc(md_path, pdf_path, override, env=env)
        pdf_bytes = pdf_path.read_bytes()
        page_count = _count_safe(pdf_bytes)
        return PdfExportResult(
            pdf_bytes=pdf_bytes,
            page_count=page_count,
            scale=layout.scale,
            filename="cv.pdf",
        )
    finally:
        override.unlink(missing_ok=True)


def _shrink(layout: _Layout) -> _Layout:
    return _Layout(
        scale=max(0.52, layout.scale - 0.035),
        gap_scale=max(0.62, layout.gap_scale - 0.045),
        line_height=max(1.1, layout.line_height - 0.018),
    )


def _find_fitting(
    md_path: Path, pdf_path: Path, *, env: dict[str, str]
) -> tuple[_Layout, PdfExportResult]:
    layout = _Layout(scale=1.0, gap_scale=1.0, line_height=1.34)
    last: PdfExportResult | None = None
    for _ in range(14):
        last = _render(md_path, pdf_path, env=env, layout=layout)
        if last.page_count <= 1:
            return layout, last
        layout = _shrink(layout)
    assert last is not None
    return layout, last


def _maximize_fill(
    md_path: Path,
    pdf_path: Path,
    *,
    env: dict[str, str],
    base: _Layout,
    seed: PdfExportResult,
) -> PdfExportResult:
    best = seed
    if best.page_count > 1:
        best = _render(md_path, pdf_path, env=env, layout=base)
    if best.page_count > 1:
        return best

    lo = base
    hi_scale = min(2.35, base.scale * 1.85)
    hi = _Layout(
        scale=hi_scale,
        gap_scale=min(1.55, base.gap_scale * (hi_scale / base.scale)),
        line_height=min(1.4, base.line_height + 0.1),
    )

    hi_trial = _render(md_path, pdf_path, env=env, layout=hi)
    if hi_trial.page_count <= 1:
        best = hi_trial
        lo = hi
        hi_scale = min(2.6, hi.scale * 1.2)
        hi = _Layout(
            scale=hi_scale,
            gap_scale=min(1.6, lo.gap_scale * (hi_scale / lo.scale)),
            line_height=min(1.42, lo.line_height + 0.06),
        )

    for _ in range(12):
        mid = _Layout(
            scale=(lo.scale + hi.scale) / 2,
            gap_scale=(lo.gap_scale + hi.gap_scale) / 2,
            line_height=(lo.line_height + hi.line_height) / 2,
        )
        trial = _render(md_path, pdf_path, env=env, layout=mid)
        if trial.page_count <= 1:
            lo = mid
            best = trial
        else:
            hi = mid

    return best


def _safe_filename(name: str) -> str:
    safe = re.sub(r"[^\w\-]+", "-", str(name or "cv"))
    safe = re.sub(r"-+", "-", safe).strip("-") or "cv"
    return f"{safe}.pdf"


def export_pdf(markdown: str, *, filename: str = "cv") -> PdfExportResult:
    if not STYLE_FILE.exists():
        raise HTTPException(503, "style.css introuvable à la racine du serveur")

    photo = settings.assets_dir / "lucas-schrever.jpg"
    if not photo.exists():
        raise HTTPException(503, f"Photo introuvable : {photo}")

    env = os.environ.copy()
    if os.name == "nt" and Path(settings.weasyprint_dll).is_dir():
        env.setdefault("WEASYPRINT_DLL_DIRECTORIES", settings.weasyprint_dll)

    md = _normalize_photo_paths(markdown)

    with tempfile.TemporaryDirectory(prefix="cv-pdf-") as tmp:
        tmp_path = Path(tmp)
        md_path = tmp_path / "cv.md"
        pdf_path = tmp_path / "cv.pdf"
        md_path.write_text(md, encoding="utf-8")

        try:
            layout, best = _find_fitting(md_path, pdf_path, env=env)
            result = _maximize_fill(
                md_path, pdf_path, env=env, base=layout, seed=best
            )
        except FileNotFoundError as exc:
            raise HTTPException(
                503,
                "Pandoc introuvable — installe Pandoc + WeasyPrint pour l'export PDF.",
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            raise HTTPException(503, f"Échec Pandoc / WeasyPrint : {detail}") from exc

    if result.page_count > 1:
        raise HTTPException(
            503,
            f"Le CV ne tient pas sur une page A4 "
            f"(pages={result.page_count}, scale={result.scale:.3f}). Réduis le contenu.",
        )

    return PdfExportResult(
        pdf_bytes=result.pdf_bytes,
        page_count=result.page_count,
        scale=result.scale,
        filename=_safe_filename(filename),
    )
