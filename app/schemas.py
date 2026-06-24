from datetime import datetime

from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    data: dict
    is_default: bool = False


class ProfileUpdate(BaseModel):
    name: str | None = None
    data: dict | None = None
    is_default: bool | None = None


class ProfileRead(BaseModel):
    id: int
    name: str
    is_default: bool
    data: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileMarkdownRead(BaseModel):
    profile_id: int
    title: str
    markdown: str
    is_default: bool = True


class JobCreate(BaseModel):
    raw_text: str = Field(min_length=10)
    label: str | None = None


class JobRead(BaseModel):
    id: int
    label: str | None
    raw_text: str
    source: str
    detected_title: str | None
    detected_tags: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateRequest(BaseModel):
    profile_id: int | None = None
    job_id: int | None = None
    job_text: str | None = None
    use_llm: bool = True


class GenerationRead(BaseModel):
    id: int
    profile_id: int
    job_id: int
    title: str
    markdown: str
    use_llm: bool
    llm_applied: bool
    warnings: list[str]
    detected_tags: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerationsPurgeRead(BaseModel):
    deleted_generations: int
    deleted_jobs: int
