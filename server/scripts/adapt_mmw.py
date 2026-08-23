"""Adaptation ciblée Make Me Win — Assistant chef de projet digital technique."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "cv.db"
OUT = Path(__file__).resolve().parent / "tmp-mmw-adapted.json"

TITLE = "Assistant chef de projet digital"
COMPANY = "Make Me Win"
FILENAME = "assistant-chef-de-projet-digital-make-me-win"

PROFIL = (
    "Assistant chef de projet digital technique, je structure la documentation produit "
    "(centre d'aide, guides, FAQ) et j'accompagne la delivery Agile d'un SaaS data. "
    "Je vulgarise le fonctionnel, aligne parties prenantes et utilisateurs, et contribue "
    "à une base de connaissances claire — y compris pour une IA interne."
)

SKILLS = """## Compétences

### Pilotage & documentation

- Agile / Scrum — sprints, rituels, backlog, priorisation
- Cadrage du scope, specs fonctionnelles & techniques
- Structuration documentaire — arborescence, FAQ, tutoriels
- Product management / vision produit
- Processus de validation, publication et contrôle qualité
- Management des parties prenantes & suivi d'avancement

### Outils documentation & SaaS

- Notion, GitBook, VitePress
- Jira, Confluence
- Aisance SaaS / interfaces web
- Contenu visuel — captures, schémas, tutoriels
- Figma — wireframes & prototypes

### Web & UX writing

- HTML5, CSS3
- UX writing / sensibilité UX
- JavaScript (bases)
- React / Vue — culture front
- WordPress — contenus & multi-sites
"""


def replace_section_body(markdown: str, titles: list[str], new_body: str) -> str:
    for title in titles:
        pattern = re.compile(
            rf"((?:^|\n)({re.escape(title)})\s*\n)([\s\S]*?)(?=\n##\s|\n</div>|$)",
            re.IGNORECASE,
        )
        if pattern.search(markdown):
            return pattern.sub(rf"\1\n{new_body.strip()}\n", markdown, count=1)
    return markdown


def replace_section_full(markdown: str, titles: list[str], new_full: str) -> str:
    for title in titles:
        pattern = re.compile(
            rf"(^|\n)({re.escape(title)})\s*\n[\s\S]*?(?=\n##\s|\n</div>|$)",
            re.IGNORECASE,
        )
        if pattern.search(markdown):
            return pattern.sub(rf"\1{new_full.strip()}\n", markdown, count=1)
    return markdown


def replace_cv_role(markdown: str, title: str) -> str:
    esc = (
        title.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return re.sub(
        r'(<p class="cv-role">)([\s\S]*?)(</p>)',
        rf"\1{esc}\3",
        markdown,
        count=1,
        flags=re.IGNORECASE,
    )


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, name, title, summary, markdown FROM profiles WHERE name = ?",
        ("Chef de projet digital",),
    ).fetchone()
    conn.close()
    if not row:
        raise SystemExit("Profil Chef de projet digital introuvable")

    md = row["markdown"]
    md = replace_section_body(md, ["## Profil", "## Summary"], PROFIL)
    md = replace_section_full(
        md,
        ["## Compétences techniques", "## Compétences", "## Technical skills", "## Skills"],
        SKILLS,
    )
    md = replace_cv_role(md, TITLE)

    result = {
        "matched": True,
        "adapted": True,
        "matched_via": "selected",
        "message": "Profil adapté · Chef de projet digital → Make Me Win",
        "reason": (
            "Titre, profil et skills recentrés documentation produit / centre d'aide / "
            "SaaS / Agile pour Assistant chef de projet digital — technique (Make Me Win)."
        ),
        "source": "curated",
        "fallback": False,
        "company": COMPANY,
        "profile": {
            "id": row["id"],
            "name": row["name"],
            "title": TITLE,
            "summary": PROFIL,
            "markdown": md,
            "filename": FILENAME,
            "company": COMPANY,
        },
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK ->", OUT)
    print("title:", TITLE)
    print("company:", COMPANY)
    print("filename:", FILENAME)
    print("profil:", PROFIL)
    print("--- skills ---")
    print(SKILLS)


if __name__ == "__main__":
    main()
