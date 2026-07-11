"""Rendu Markdown du CV."""

from __future__ import annotations

from app.config import PHOTO_PATH
from app.services.llm import CvAdaptation
from app.services.skills_display import filter_categories_for_cv


def sort_by_date(items: list) -> list:
    return sorted(items, key=lambda item: item.get("sort_key", 999))


def _bullet_texts(exp: dict) -> list[str]:
    return [b if isinstance(b, str) else b["text"] for b in exp.get("bullets", [])]


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


def render_header(data: dict, title: str) -> str:
    header = data["header"]
    photo = header.get("photo", PHOTO_PATH)
    if photo in {"lucas-schrever.jpg", "photo.jpg"}:
        photo = PHOTO_PATH
    return f"""<header class="cv-header">
<div class="cv-header-main">
<p class="cv-name">{header['name']}</p>
<p class="cv-role">{title}</p>
{_render_contact(header)}
</div>
<img class="photo" src="{photo}" alt="" />
</header>"""


def render_experiences(data: dict, adaptation: CvAdaptation | None = None) -> str:
    lines = ["## Expériences Professionnelles", ""]
    for exp in sort_by_date(data["experiences"]):
        lines.append(f"### {exp['title']} — {exp['company']} *{exp['dates']}*")
        lines.append("")
        if adaptation and exp["id"] in adaptation.bullets:
            bullets = adaptation.bullets[exp["id"]]
        else:
            bullets = _bullet_texts(exp)
        lines += [f"- {text}" for text in bullets]
        lines.append("")
    return "\n".join(lines).rstrip()


def render_formations(data: dict, adaptation: CvAdaptation | None = None) -> str:
    lines = ["## Formations", ""]
    for f in sort_by_date(data["formations"]):
        lines.append(f"### {f['title']} — {f['school']} *{f['dates']}*")
        lines.append("")
        bullets = f.get("bullets", [])
        fid = f.get("id", f["school"])
        if adaptation and adaptation.formation_bullets and fid in adaptation.formation_bullets:
            bullets = adaptation.formation_bullets[fid]
        for bullet in bullets:
            lines.append(f"- {bullet}")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_skill_groups(skill_groups: list[dict], *, english: bool = False) -> str:
    filtered = filter_categories_for_cv(skill_groups)
    if not filtered:
        return ""
    title = "## Technical Skills" if english else "## Compétences techniques"
    lines = [title, ""]
    for group in filtered:
        lines.append(f"### {group['label']}")
        lines.append("")
        for item in group["items"]:
            # « Parent — sub1, sub2 » : une ligne par skill (+ subskills)
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_certifications(data: dict, adaptation: CvAdaptation | None = None) -> str:
    text = adaptation.certifications if adaptation and adaptation.certifications else data["certifications"]
    return "\n".join(["## Certifications", "", text, ""])


def render_langues(data: dict, *, english: bool = False, adaptation: CvAdaptation | None = None) -> str:
    title = "## Languages" if english else "## Langues"
    lines = [title, ""]
    langues = adaptation.langues if adaptation and adaptation.langues else data["langues"]
    lines += [f"- {lang}" for lang in langues]
    return "\n".join(lines)


def build_markdown(
    data: dict,
    *,
    title: str,
    adaptation: CvAdaptation | None = None,
    english: bool = False,
) -> str:
    profil = (adaptation.profil if adaptation and adaptation.profil else "").strip()
    section_profile = "## Summary" if english else "## Profil"
    skills_block = render_skill_groups(
        adaptation.skill_groups if adaptation else [],
        english=english,
    )

    parts = [
        '<div class="cv-page">',
        render_header(data, title),
        "",
        section_profile,
        "",
        profil,
        "",
        render_experiences(data, adaptation),
        "",
        render_formations(data, adaptation),
    ]
    if skills_block:
        parts += ["", skills_block]
    parts += [
        "",
        render_certifications(data, adaptation),
        render_langues(data, english=english, adaptation=adaptation),
        "</div>",
        "",
    ]
    return "\n".join(parts)
