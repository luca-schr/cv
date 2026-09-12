from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    settings.database_url  # ensure path resolved
    db_path = settings.database_url.replace("sqlite:///", "")
    from pathlib import Path

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()


def _ensure_sqlite_columns() -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "generations" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("generations")}
    if "match_report" in columns:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE generations ADD COLUMN match_report TEXT"))
