from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  label_fr TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
  is_default INTEGER NOT NULL DEFAULT 0,
  title TEXT,
  title_en TEXT,
  summary TEXT,
  summary_en TEXT,
  markdown TEXT NOT NULL,
  markdown_en TEXT,
  keywords TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_profiles_category ON profiles(category_id);
CREATE INDEX IF NOT EXISTS idx_profiles_name ON profiles(name);
"""


def _connect() -> sqlite3.Connection:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.database_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(SCHEMA)
        seed_if_empty(conn)


def seed_if_empty(conn: sqlite3.Connection) -> None:
    n = conn.execute("SELECT COUNT(*) AS n FROM categories").fetchone()["n"]
    if n == 0:
        _seed_all(conn)
        return
    _ensure_default_profile(conn)
    _insert_missing_profiles(conn)


def _read_seed() -> dict[str, Any]:
    seed_path: Path = settings.seed_data_path
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed introuvable : {seed_path}")
    return json.loads(seed_path.read_text(encoding="utf-8"))


def _category_ids(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        r["name"]: r["id"]
        for r in conn.execute("SELECT id, name FROM categories").fetchall()
    }


def _profile_values(p: dict[str, Any], cats: dict[str, int]) -> tuple[Any, ...]:
    return (
        p["name"],
        cats[p["category"]],
        1 if p.get("is_default") else 0,
        p.get("title"),
        p.get("title_en"),
        p.get("summary"),
        p.get("summary_en"),
        p["markdown"],
        p.get("markdown_en"),
        p.get("keywords"),
    )


def _insert_profile(
    conn: sqlite3.Connection, p: dict[str, Any], cats: dict[str, int]
) -> None:
    conn.execute(
        """
        INSERT INTO profiles (
          name, category_id, is_default, title, title_en,
          summary, summary_en, markdown, markdown_en, keywords
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        _profile_values(p, cats),
    )


def _seed_all(conn: sqlite3.Connection) -> None:
    data = _read_seed()
    for cat in data.get("categories", []):
        conn.execute(
            "INSERT INTO categories (name, label_fr) VALUES (?, ?)",
            (cat["name"], cat["label_fr"]),
        )
    cats = _category_ids(conn)
    for p in data.get("profiles", []):
        _insert_profile(conn, p, cats)


def _ensure_default_profile(conn: sqlite3.Connection) -> None:
    has_default = conn.execute(
        "SELECT id FROM profiles WHERE is_default = 1 LIMIT 1"
    ).fetchone()
    if has_default:
        return
    row = conn.execute(
        "SELECT id FROM profiles WHERE name LIKE '%Fullstack%' OR name LIKE '%fullstack%' LIMIT 1"
    ).fetchone()
    if row:
        conn.execute("UPDATE profiles SET is_default = 1 WHERE id = ?", (row["id"],))


def _insert_missing_profiles(conn: sqlite3.Connection) -> None:
    data = _read_seed()
    cats = _category_ids(conn)
    existing = {r["name"] for r in conn.execute("SELECT name FROM profiles").fetchall()}
    for p in data.get("profiles", []):
        if p["name"] in existing or p["category"] not in cats:
            continue
        _insert_profile(conn, p, cats)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)
