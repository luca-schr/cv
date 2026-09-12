from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON cv-data
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    generations: Mapped[list["Generation"]] = relationship(back_populates="profile")


class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str | None] = mapped_column(String(200))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="text")
    detected_title: Mapped[str | None] = mapped_column(String(200))
    detected_tags: Mapped[str | None] = mapped_column(Text)  # JSON list
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    generations: Mapped[list["Generation"]] = relationship(back_populates="job")


class Generation(Base):
    __tablename__ = "generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_postings.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200))
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    use_llm: Mapped[bool] = mapped_column(Boolean, default=True)
    llm_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    warnings: Mapped[str | None] = mapped_column(Text)  # JSON list
    match_report: Mapped[str | None] = mapped_column(Text)  # JSON match panel
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    profile: Mapped["Profile"] = relationship(back_populates="generations")
    job: Mapped["JobPosting"] = relationship(back_populates="generations")
