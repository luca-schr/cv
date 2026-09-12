"""Schémas Pydantic pour le pipeline LLM (extraction, match, réécriture)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _clean_str_list(values: list) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in values or []:
        item = " ".join(str(raw).split()).strip(" •-*")
        key = item.lower()
        if len(item) < 2 or key in seen:
            continue
        seen.add(key)
        out.append(item[:80])
    return out


class JobBrief(BaseModel):
    title: str = ""
    company: str | None = None
    keywords: list[str] = Field(default_factory=list)
    hard_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    missions: list[str] = Field(default_factory=list)
    must_haves: list[str] = Field(default_factory=list)

    @field_validator("title", mode="before")
    @classmethod
    def _title(cls, value: object) -> str:
        return str(value or "").strip()[:90]

    @field_validator("company", mode="before")
    @classmethod
    def _company(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if text.lower() in {"", "null", "none"}:
            return None
        return text[:80]

    @field_validator(
        "keywords", "hard_skills", "soft_skills", "missions", "must_haves", mode="before"
    )
    @classmethod
    def _lists(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return _clean_str_list(value)


class SkillHit(BaseModel):
    term: str
    status: Literal["matched", "gap"]
    evidence: str | None = None


class MatchReport(BaseModel):
    score: float = 0.0
    matched: list[str] = Field(default_factory=list)
    emphasize: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    vocabulary: list[str] = Field(default_factory=list)
    hits: list[SkillHit] = Field(default_factory=list)

    def to_public(self) -> dict:
        return {
            "score": round(self.score, 3),
            "matched": self.matched,
            "emphasize": self.emphasize,
            "gaps": self.gaps,
            "vocabulary": self.vocabulary[:16],
        }


class CompetenceCat(BaseModel):
    label: str
    items: list[str] = Field(default_factory=list)

    @field_validator("label", mode="before")
    @classmethod
    def _label(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("items", mode="before")
    @classmethod
    def _items(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return _clean_str_list(value)


class AdaptationPayload(BaseModel):
    title: str = ""
    profil: str = ""
    competences: list[CompetenceCat] = Field(default_factory=list)
    bullets: dict[str, list[str]] = Field(default_factory=dict)
    formation_bullets: dict[str, list[str]] = Field(default_factory=dict)
    certifications: str = ""
    langues: list[str] = Field(default_factory=list)

    @field_validator("title", "profil", "certifications", mode="before")
    @classmethod
    def _text(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("langues", mode="before")
    @classmethod
    def _langues(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return _clean_str_list(value)

    @field_validator("bullets", "formation_bullets", mode="before")
    @classmethod
    def _bullet_maps(cls, value: object) -> dict[str, list[str]]:
        if not isinstance(value, dict):
            return {}
        out: dict[str, list[str]] = {}
        for key, items in value.items():
            if not isinstance(items, list):
                continue
            cleaned = [str(item).strip() for item in items if str(item).strip()]
            if cleaned:
                out[str(key)] = cleaned
        return out
