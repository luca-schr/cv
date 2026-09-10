"""Rendu Markdown du CV."""

from __future__ import annotations

from app.config import PHOTO_PATH
from app.services.analyzer import JobAnalysis
from app.services.competences import normalize_competences
from app.services.llm import LLMAdaptation


def sort_by_date(items: list) -> list:
    return sorted(items, key=lambda item: item.get("sort_key", 999))


def _bullet_texts(exp: dict) -> list[str]:
    return [b if isinstance(b, str) else b["text"] for b in exp.get("bullets", [])]


def _item_terms(items: list) -> list[str]:
    return [i if isinstance(i, str) else i["term"] for i in items]


def _render_contact(header: dict) -> str:
    contact = header.get("contact")
    email = header.get("email", "")

    if isinstance(contact, dict):
        parts = [p for p in (contact.get("location"), contact.get("phone")) if p]
        if email:
            parts.append(f'<a href="mailto:{email}">{email}</a>')
        line1 = " · ".join(parts)
        links = contact.get("links") or []
        line2 = " · ".join(
            f'<a href="{link["url"]}">{link["label"]}</a>' for link in links if link.get("url")
        )
        blocks = [f'<p class="cv-contact-primary">{line1}</p>']
        if line2:
            blocks.append(f'<p class="cv-contact-links">{line2}</p>')
        return "\n".join(blocks)

    return f'<p class="cv-contact-primary">{contact or ""}</p>'


def _format_langue(langue: str | dict) -> str:
    if isinstance(langue, dict):
        return " ; ".join(f"{k} : {v}" for k, v in langue.items())
    return str(langue)


def render_header(data: dict, title: str) -> str:
    header = data["header"]
    contact = _render_contact(header)
    photo = header.get("photo", PHOTO_PATH)
    if photo in {"lucas-schrever.jpg", "photo.jpg", "DSC02211.jpg"}:
        photo = PHOTO_PATH
    return f"""<header class="cv-header">
<div class="cv-header-main">
<h1 class="cv-role">{title}</h1>
<p class="cv-name">{header['name']}</p>
{contact}
</div>
<img class="photo" src="{photo}" alt="" />
</header>"""


def render_experiences(data: dict, llm: LLMAdaptation | None = None) -> str:
    lines = ["## Expériences Professionnelles", ""]
    for exp in sort_by_date(data["experiences"]):
        lines.append(
            f"### {exp['title']} - {exp['company']} "
            f'<span class="cv-dates">{exp["dates"]}</span>'
        )
        lines.append("")
        if llm and exp["id"] in llm.bullets:
            bullets = llm.bullets[exp["id"]]
        else:
            bullets = _bullet_texts(exp)
        lines += [f"- {text}" for text in bullets]
        lines.append("")
    return "\n".join(lines).rstrip()


def render_formations(data: dict, llm: LLMAdaptation | None = None) -> str:
    lines = ["## Formations", ""]
    for f in sort_by_date(data["formations"]):
        lines.append(
            f"### {f['title']} - {f['school']} "
            f'<span class="cv-dates">{f["dates"]}</span>'
        )
        lines.append("")
        bullets = f.get("bullets", [])
        fid = f.get("id", f["school"])
        if llm and llm.formation_bullets and fid in llm.formation_bullets:
            bullets = llm.formation_bullets[fid]
        for bullet in bullets:
            lines.append(f"- {bullet}")
        if f.get("description") and not bullets:
            lines.append(f"- {f['description']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_profil_section(data: dict, llm_profil: str | None = None) -> str:
    profil_block = data.get("profil", {})
    return (llm_profil or profil_block.get("text", "")).strip()


def render_competences(competences: list[dict], *, english: bool = False) -> str:
    ordered = normalize_competences(competences, english=english)
    if not ordered:
        return ""
    lines = ["## Compétences techniques", ""]
    for cat in ordered:
        label = cat.get("label", "")
        terms = _item_terms(cat.get("items", []))
        if not label or not terms:
            continue
        lines += [f"### {label}", "", f"{', '.join(terms)}", ""]
    return "\n".join(lines).rstrip()


def render_certifications(data: dict, llm: LLMAdaptation | None = None) -> str:
    text = data["certifications"]
    if llm and llm.certifications:
        text = llm.certifications
    return "\n".join(["## Certifications", "", text, ""])


def render_langues(data: dict, *, english: bool = False, llm: LLMAdaptation | None = None) -> str:
    title = "## Languages" if english else "## Langues"
    lines = [title, ""]
    langues = llm.langues if llm and llm.langues else data["langues"]
    lines += [f"- {_format_langue(lang)}" for lang in langues]
    return "\n".join(lines)


def build_markdown(
    data: dict,
    analysis: JobAnalysis | None = None,
    llm: LLMAdaptation | None = None,
    title: str | None = None,
    english: bool = False,
) -> str:
    resolved_title = title or data["header"]["title_default"]
    llm_active = llm if llm and llm.used_llm else None

    if llm_active and llm_active.profil:
        profil = render_profil_section(data, llm_active.profil)
    else:
        profil = render_profil_section(data)

    if llm_active and llm_active.competences:
        competences = normalize_competences(llm_active.competences, english=english)
    else:
        competences = normalize_competences(data.get("competences", []), english=english)

    section_profile = "## Summary" if english else "## Profil"
    section_experiences = "## Professional Experience" if english else "## Expériences Professionnelles"
    section_education = "## Education" if english else "## Formations"
    section_skills = "## Technical Skills" if english else "## Compétences techniques"
    section_certs = "## Certifications"
    section_langs = "## Languages" if english else "## Langues"

    skills_block = render_competences(competences, english=english).replace(
        "## Compétences techniques", section_skills, 1
    )

    return "\n".join(
        [
            '<div class="cv-page">',
            render_header(data, resolved_title),
            "",
            section_profile,
            "",
            profil,
            "",
            render_experiences(data, llm_active).replace(
                "## Expériences Professionnelles", section_experiences, 1
            ),
            "",
            render_formations(data, llm_active).replace("## Formations", section_education, 1),
            "",
            skills_block,
            "",
            render_certifications(data, llm_active).replace("## Certifications", section_certs, 1),
            render_langues(data, english=english, llm=llm_active).replace(
                "## Langues", section_langs, 1
            ),
            "</div>",
            "",
        ]
    )
