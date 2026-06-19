"""
Génère un CV Markdown (et optionnellement le PDF) adapté à une fiche de poste.

Usage:
  python build.py --master
  python build.py jobs/mon-offre.txt
  python build.py jobs/mon-offre.txt --md-only

Fichier jobs/*.txt : URL seule ou texte brut de l'offre.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

from cv_builder.job_analyzer import analyze_job
from cv_builder.job_source import load_job_text
from cv_builder.llm_adapt import adapt_with_llm, load_llm_config
from cv_builder.render import build_markdown

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "cv-data.yaml"
STYLE_FILE = ROOT / "style.css"
OUTPUT_DIR = ROOT / "output"


def load_cv_data() -> dict:
    with DATA_FILE.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
    return slug.strip("-") or "cv"


def run_pandoc(md_path: Path, pdf_path: Path) -> None:
    env = os.environ.copy()
    env.setdefault("WEASYPRINT_DLL_DIRECTORIES", r"C:\msys64\mingw64\bin")
    subprocess.run(
        [
            "pandoc",
            str(md_path),
            "-o",
            str(pdf_path),
            "--pdf-engine=weasyprint",
            f"--css={STYLE_FILE}",
        ],
        check=True,
        env=env,
        cwd=ROOT,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Génère un CV adapté à une fiche de poste.")
    parser.add_argument("job_file", nargs="?", help="Fichier dans jobs/ (URL ou texte)")
    parser.add_argument("--master", action="store_true", help="Génère cv.md sans filtre offre")
    parser.add_argument("--md-only", action="store_true", help="Ne pas générer le PDF")
    parser.add_argument("--llm", action="store_true", help="Réécriture intelligente (LLM)")
    parser.add_argument("--no-llm", action="store_true", help="Désactiver le LLM")
    args = parser.parse_args()

    data = load_cv_data()
    analysis = None
    llm_adaptation = None
    use_llm = not args.no_llm and (args.llm or load_llm_config().get("enabled", False))

    if args.master:
        md_path = ROOT / "cv.md"
    elif args.job_file:
        job_path = Path(args.job_file)
        if not job_path.is_absolute():
            job_path = ROOT / job_path
        if not job_path.exists():
            print(f"Fichier introuvable : {job_path}", file=sys.stderr)
            return 1

        try:
            raw_text, source = load_job_text(job_path)
        except (ValueError, RuntimeError) as exc:
            print(str(exc), file=sys.stderr)
            return 1

        analysis = analyze_job(raw_text, source, data["header"]["title_default"])
        if use_llm and not args.master:
            llm_adaptation = adapt_with_llm(analysis, data, force=args.llm)
        OUTPUT_DIR.mkdir(exist_ok=True)
        md_path = OUTPUT_DIR / f"cv-{slugify(job_path.stem)}.md"
    else:
        parser.print_help()
        return 1

    markdown = build_markdown(
        data,
        analysis,
        llm_adaptation if llm_adaptation and llm_adaptation.used_llm else None,
    )
    md_path.write_text(markdown, encoding="utf-8")
    print(f"Markdown généré : {md_path}")

    if not args.md_only:
        pdf_path = md_path.with_suffix(".pdf")
        try:
            run_pandoc(md_path, pdf_path)
            print(f"PDF généré : {pdf_path}")
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            print(f"PDF non généré ({exc}). Markdown disponible.", file=sys.stderr)

    if analysis:
        print(f"Source : {analysis.source}")
        print(f"Titre détecté : {analysis.title}")
        print(f"Tags détectés ({len(analysis.tags)}) : {', '.join(sorted(analysis.tags)) or 'aucun'}")
        if llm_adaptation:
            if llm_adaptation.used_llm:
                print("LLM : réécriture appliquée")
                if llm_adaptation.title:
                    print(f"Titre final : {llm_adaptation.title}")
            for warning in llm_adaptation.warnings:
                print(f"Attention : {warning}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
