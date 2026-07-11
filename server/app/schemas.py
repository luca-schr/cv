from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    job_text: str = Field(min_length=10)
    english: bool = False
    temperature: float = Field(default=0.45, ge=0.2, le=0.8)


class GenerateResponse(BaseModel):
    id: int
    title: str
    company: str | None
    markdown: str
    warnings: list[str] = []
    page_count: int | None = None
    version: int = 1
    filename: str = "cv"


class ExportPdfRequest(BaseModel):
    markdown: str = Field(min_length=1)
    filename: str | None = None
    title: str | None = None
    company: str | None = None
    version: int | None = None


class GenerationSummary(BaseModel):
    id: int
    title: str
    company: str | None
    version: int = 1
    filename: str = "cv"
    created_at: datetime


class GenerationDetail(GenerationSummary):
    markdown: str
    job_text: str | None = None


class SkillOut(BaseModel):
    id: int
    name: str
    level: int | None
    source: str
    preferred: bool = False
    subskills: list["SubskillOut"] = []


class SubskillOut(BaseModel):
    id: int
    name: str
    level: int | None
    source: str
    parent_skill_id: int


class CategoryOut(BaseModel):
    id: int
    name: str
    source: str
    skills: list[SkillOut]


class ProfileSkillsOut(BaseModel):
    categories: list[CategoryOut]
