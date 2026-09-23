"""SQLite : personne, liens, profils bilingues (markdown FR/EN)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB_PATH = DATA / "cv.sqlite"


def connect() -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS person (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            photo TEXT,
            location_fr TEXT,
            location_en TEXT
        );

        CREATE TABLE IF NOT EXISTS person_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sort_order INTEGER NOT NULL,
            label_fr TEXT,
            label_en TEXT,
            url TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS profiles (
            id TEXT PRIMARY KEY,
            sort_order INTEGER NOT NULL,
            title_fr TEXT,
            title_en TEXT,
            hide_links TEXT,
            payload TEXT NOT NULL DEFAULT '{}',
            markdown_fr TEXT,
            markdown_en TEXT
        );
        """
    )
    conn.commit()


def init_db() -> None:
    with connect() as conn:
        init_schema(conn)


def _profile_from_row(row: sqlite3.Row) -> dict:
    hide = json.loads(row["hide_links"] or "[]")
    markdown: dict[str, str] = {}
    if row["markdown_fr"]:
        markdown["fr"] = row["markdown_fr"]
    if row["markdown_en"]:
        markdown["en"] = row["markdown_en"]
    return {
        "id": row["id"],
        "profile": {"fr": row["title_fr"] or "", "en": row["title_en"] or ""},
        "hideLinks": hide,
        "markdown": markdown,
    }


def load_person() -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM person WHERE id = 1").fetchone()
        if not row:
            raise RuntimeError("Personne absente de cv.sqlite")
        links = conn.execute(
            "SELECT label_fr, label_en, url FROM person_links ORDER BY sort_order, id"
        ).fetchall()
    return {
        "name": row["name"],
        "email": row["email"] or "",
        "phone": row["phone"] or "",
        "photo": row["photo"] or "",
        "location": {"fr": row["location_fr"] or "", "en": row["location_en"] or ""},
        "links": [
            {
                "label": {"fr": link["label_fr"] or "", "en": link["label_en"] or ""},
                "url": link["url"],
            }
            for link in links
        ],
    }


def list_profile_summaries() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, title_fr, title_en FROM profiles ORDER BY sort_order, id"
        ).fetchall()
    return [
        {"id": row["id"], "profile": {"fr": row["title_fr"] or "", "en": row["title_en"] or ""}}
        for row in rows
    ]


def get_profile(profile_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM profiles WHERE id = ?", (profile_id,)
        ).fetchone()
    return _profile_from_row(row) if row else None


def save_profile_markdown(profile_id: str, lang: str, markdown: str) -> bool:
    column = "markdown_en" if lang == "en" else "markdown_fr"
    with connect() as conn:
        cur = conn.execute(
            f"UPDATE profiles SET {column} = ? WHERE id = ?",
            (markdown.strip(), profile_id),
        )
        conn.commit()
        return cur.rowcount > 0


def save_profile_pair(
    profile_id: str,
    source_lang: str,
    source_markdown: str,
    other_markdown: str | None,
) -> bool:
    source_col = "markdown_en" if source_lang == "en" else "markdown_fr"
    other_col = "markdown_fr" if source_lang == "en" else "markdown_en"
    with connect() as conn:
        if other_markdown and other_markdown.strip():
            cur = conn.execute(
                f"UPDATE profiles SET {source_col} = ?, {other_col} = ? WHERE id = ?",
                (source_markdown.strip(), other_markdown.strip(), profile_id),
            )
        else:
            cur = conn.execute(
                f"UPDATE profiles SET {source_col} = ? WHERE id = ?",
                (source_markdown.strip(), profile_id),
            )
        conn.commit()
        return cur.rowcount > 0
