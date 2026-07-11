from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


_db_ready = False


class Base(DeclarativeBase):
    pass


def ensure_db() -> None:
    global _db_ready
    if _db_ready:
        return
    init_db()
    _db_ready = True


def get_db() -> Generator[Session, None, None]:
    ensure_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    db_path = settings.database_url.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _migrate_generations_columns()


def _migrate_generations_columns() -> None:
    """Ajoute colonnes version / export_filename sur bases existantes."""
    import sqlite3

    from app.services.filename import build_export_filename

    db_path = settings.database_url.replace("sqlite:///", "")
    if not Path(db_path).exists():
        return
    conn = sqlite3.connect(db_path)
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(generations)")}
        added_cols = False
        if "version" not in cols:
            conn.execute("ALTER TABLE generations ADD COLUMN version INTEGER NOT NULL DEFAULT 1")
            added_cols = True
        if "export_filename" not in cols:
            conn.execute(
                "ALTER TABLE generations ADD COLUMN export_filename VARCHAR(220) NOT NULL DEFAULT 'cv'"
            )
            added_cols = True
        conn.commit()

        if not added_cols:
            return

        rows = conn.execute(
            "SELECT id, title, company, version FROM generations WHERE export_filename = 'cv' OR export_filename IS NULL"
        ).fetchall()
        for gen_id, title, company, version in rows:
            ver = version or 1
            slug = build_export_filename(title or "cv", company, version=ver)
            conn.execute(
                "UPDATE generations SET export_filename = ?, version = ? WHERE id = ?",
                (slug, ver, gen_id),
            )
        conn.commit()
    finally:
        conn.close()
