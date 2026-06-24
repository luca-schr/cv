"""Rendu Markdown du CV."""

from __future__ import annotations

from app.config import PHOTO_PATH
from app.services.analyzer import JobAnalysis, load_analysis_config
from app.services.llm import LLMAdaptation
from app.services.title_resolver import resolve_title


def score_tags(item_tags: list[str], job_tags: set[str]) -> int:
    return sum(1 for tag in item_tags if tag in job_tags)


def sort_by_relevance(items: list, job_tags: set[str], tag_key: str = "tags") -> list:
    if not job_tags:
        return items
    return sorted(items, key=lambda item: score_tags(item.get(tag_key, []), job_tags), reverse=True)


def sort_by_date(items: list) -> list:
    return sorted(items, key=lambda item: item.get("sort_key", 999))


def _bullet_limit(scoring: dict, experience_index: int) -> int:
    recent = int(scoring.get("max_bullets_recent", 3))
    older = int(scoring.get("max_bullets_older", 2))
    return recent if experience_index < 2 else older


def _select_bullets(exp: dict, job_tags: set[str], limit: int) -> list[str]:
    bullets = exp["bullets"]
    if job_tags:
        bullets = sort_by_relevance(bullets, job_tags)
    return [b["text"] for b in bullets[:limit]]
def build_profil(data: dict, job_tags: set[str], limit: int, llm: LLMAdaptation | None = None) -> str:
    if llm and llm.profil:
        return llm.profil
    profil = data["profil"]
    if not job_tags and profil.get("text"):
        return profil["text"]
    keywords = profil["keywords"]
    if job_tags:
        ranked = sort_by_relevance(keywords, job_tags, "tags")
        matched = [item["term"] for item in ranked if score_tags(item["tags"], job_tags) > 0]
        rest = [item["term"] for item in ranked if item["term"] not in matched]
        terms = (matched + rest)[:limit]
        stack = ", ".join(terms)
        return f"{profil['intro']} Expertise : {stack}. {profil['closing']}"
    if profil.get("text"):
        return profil["text"]
    terms = [item["term"] for item in keywords[:limit]]
    return f"{profil['intro']} {', '.join(terms)}. {profil['closing']}"


def _mailto_contact(contact: str, email: str | None) -> str:
    if not email:
        return contact
    mailto = f"[{email}](mailto:{email})"
    if mailto in contact or f"mailto:{email}" in contact:
        return contact
    if email in contact:
        return contact.replace(email, mailto)
    return f"{contact.strip().rstrip(',')}, {mailto}"


def _format_langue(langue: str | dict) -> str:
    if isinstance(langue, dict):
        return " ; ".join(f"{k} : {v}" for k, v in langue.items())
    return str(langue)


def render_header(data: dict, title: str) -> str:
    header = data["header"]
    contact = _mailto_contact(header["contact"], header.get("email"))
    photo = header.get("photo", PHOTO_PATH)
    if photo in {"lucas-schrever.jpg", "photo.jpg"}:
        photo = PHOTO_PATH
    return f"""<header class="cv-header">

<div markdown="1">

# {header['name']}

**{title}**

{contact}

</div>

![]({photo}){{.photo}}

</header>"""


def render_experiences(
    data: dict,
    job_tags: set[str],
    scoring: dict,
    llm: LLMAdaptation | None = None,
) -> str:
    lines = ["## Expériences Professionnelles", ""]
    experiences = sort_by_date(data["experiences"])
    for index, exp in enumerate(experiences):
        limit = _bullet_limit(scoring, index)
        lines.append(f"### {exp['title']} — {exp['company']} *{exp['dates']}*")
        lines.append("")
        if llm and exp["id"] in llm.bullets:
            bullets = llm.bullets[exp["id"]][:limit]
        else:
            bullets = _select_bullets(exp, job_tags, limit)
        lines += [f"- {text}" for text in bullets]
        lines.append("")
    return "\n".join(lines).rstrip()


def render_formations(data: dict) -> str:
    lines = ["## Formations", ""]
    for f in sort_by_date(data["formations"]):
        lines.append(f"### {f['title']} — {f['school']} *{f['dates']}*")
        lines.append("")
        for bullet in f.get("bullets", []):
            lines.append(f"- {bullet}")
        if f.get("description") and not f.get("bullets"):
            lines.append(f"- {f['description']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _competence_label(label: str) -> str:
    lower = label.lower()
    if "front" in lower:
        return "Front-end"
    if "back" in lower:
        return "Back-end"
    return label


def _order_competence_categories(categories: list, job_tags: set[str]) -> list:
    front = [c for c in categories if "front" in c["label"].lower()]
    back = [c for c in categories if "back" in c["label"].lower()]
    others = [c for c in categories if c not in front and c not in back]
    if job_tags:
        others = sort_by_relevance(others, job_tags)
    return front + back + others


def render_competences(data: dict, job_tags: set[str]) -> str:
    lines = ["## Compétences techniques", ""]
    for cat in _order_competence_categories(data["competences"], job_tags):
        items = sort_by_relevance(cat["items"], job_tags) if job_tags else cat["items"]
        label = _competence_label(cat["label"])
        lines += [f"### {label}", "", f"{', '.join(i['term'] for i in items)}", ""]
    return "\n".join(lines).rstrip()


def render_certifications(data: dict) -> str:
    return "\n".join(["## Certifications", "", data["certifications"], ""])


def render_langues(data: dict) -> str:
    lines = ["## Langues", ""]
    lines += [f"- {_format_langue(lang)}" for lang in data["langues"]]
    return "\n".join(lines)


def build_markdown(
    data: dict,
    analysis: JobAnalysis | None = None,
    llm: LLMAdaptation | None = None,
) -> str:
    config = load_analysis_config()
    scoring = config.get("scoring", {})
    profil_limit = int(scoring.get("profil_keyword_limit", 8))
    job_tags = analysis.tags if analysis else set()
    detected = analysis.title if analysis else ""
    title = resolve_title(data, job_tags, detected)
    llm_exp = llm if llm and llm.used_llm else None
    profil = build_profil(data, job_tags, profil_limit, llm_exp)
    return "\n".join(
        [
            render_header(data, title),
            "",
            "## Profil",
            "",
            profil,
            "",
            render_experiences(data, job_tags, scoring, llm_exp),
            "",
            render_formations(data),
            "",
            render_competences(data, job_tags),
            "",
            render_certifications(data),
            render_langues(data),
            "",
        ]
    )
