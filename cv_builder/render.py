"""Rendu Markdown du CV."""

from __future__ import annotations

from cv_builder.job_analyzer import JobAnalysis, load_analysis_config
from cv_builder.llm_adapt import LLMAdaptation


def score_tags(item_tags: list[str], job_tags: set[str]) -> int:
    return sum(1 for tag in item_tags if tag in job_tags)


def sort_by_relevance(items: list, job_tags: set[str], tag_key: str = "tags") -> list:
    if not job_tags:
        return items
    return sorted(items, key=lambda item: score_tags(item.get(tag_key, []), job_tags), reverse=True)


def score_experience(exp: dict, job_tags: set[str], title_weight: int) -> int:
    score = score_tags(exp.get("title_tags", []), job_tags) * title_weight
    for bullet in exp["bullets"]:
        score += score_tags(bullet.get("tags", []), job_tags)
    return score


def build_profil(data: dict, job_tags: set[str], limit: int) -> str:
    keywords = data["profil"]["keywords"]
    if job_tags:
        ranked = sort_by_relevance(keywords, job_tags, "tags")
        matched = [item["term"] for item in ranked if score_tags(item["tags"], job_tags) > 0]
        rest = [item["term"] for item in ranked if item["term"] not in matched]
        terms = (matched + rest)[:limit]
    else:
        terms = [item["term"] for item in keywords[:limit]]
    stack = ", ".join(terms) + "."
    return f"{data['profil']['intro']} {stack} {data['profil']['closing']}"


def _mailto_contact(contact: str, email: str | None) -> str:
    if not email:
        return contact
    mailto = f"[{email}](mailto:{email})"
    if mailto in contact or f"mailto:{email}" in contact:
        return contact
    if email in contact:
        return contact.replace(email, mailto)
    return f"{contact.strip().rstrip(',')}, {mailto}"


def render_header(data: dict, title: str) -> str:
    header = data["header"]
    contact = _mailto_contact(header["contact"], header.get("email"))
    return f"""<header class="cv-header">

<div markdown="1">

# {header['name']}

**{title}**

{contact}

</div>

![]({header['photo']}){{.photo}}

</header>"""


def render_experiences(
    data: dict,
    job_tags: set[str],
    title_weight: int,
    llm: LLMAdaptation | None = None,
) -> str:
    lines = ["## Expérience professionnelle", ""]
    experiences = data["experiences"]

    if llm and llm.experience_order:
        order_map = {exp_id: index for index, exp_id in enumerate(llm.experience_order)}
        experiences = sorted(experiences, key=lambda exp: order_map.get(exp["id"], 999))
    elif job_tags:
        experiences = sorted(
            experiences,
            key=lambda exp: score_experience(exp, job_tags, title_weight),
            reverse=True,
        )

    for exp in experiences:
        lines.append(f"### {exp['title']} - {exp['company']}")
        lines.append("")
        lines.append(f"*{exp['dates']}*")
        lines.append("")

        if llm and exp["id"] in llm.bullets:
            bullet_texts = llm.bullets[exp["id"]]
        else:
            bullet_texts = [
                bullet["text"]
                for bullet in sort_by_relevance(exp["bullets"], job_tags)
            ]

        for text in bullet_texts:
            lines.append(f"- {text}")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_formations(data: dict, job_tags: set[str]) -> str:
    lines = ["## Formation", ""]
    for formation in sort_by_relevance(data["formations"], job_tags):
        lines.append(f"### {formation['title']} - {formation['school']}")
        lines.append("")
        lines.append(f"*{formation['dates']}*")
        lines.append("")
        lines.append(formation["description"])
        lines.append("")
    return "\n".join(lines).rstrip()


def render_competences(data: dict, job_tags: set[str]) -> str:
    lines = ["## Compétences techniques", ""]
    for category in sort_by_relevance(data["competences"], job_tags):
        items = sort_by_relevance(category["items"], job_tags)
        terms = ", ".join(item["term"] for item in items)
        lines.append(f"{category['label']} : {terms}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _format_langue(langue: str | dict) -> str:
    if isinstance(langue, dict):
        return " ; ".join(f"{key} : {value}" for key, value in langue.items())
    return str(langue)


def render_certifications(data: dict) -> str:
    lines = [
        "## Certifications et langues",
        "",
        f"Certifications : {data['certifications']}",
        "",
        "### Langues",
        "",
    ]
    lines.extend(f"- {_format_langue(langue)}" for langue in data["langues"])
    return "\n".join(lines)


def build_markdown(
    data: dict,
    analysis: JobAnalysis | None = None,
    llm: LLMAdaptation | None = None,
) -> str:
    config = load_analysis_config()
    scoring = config.get("scoring", {})
    title_weight = int(scoring.get("experience_title_tag_weight", 3))
    profil_limit = int(scoring.get("profil_keyword_limit", 12))

    job_tags = analysis.tags if analysis else set()
    title = analysis.title if analysis else data["header"]["title_default"]
    if llm and llm.title:
        title = llm.title

    profil = build_profil(data, job_tags, profil_limit)
    if llm and llm.profil:
        profil = llm.profil

    parts = [
        render_header(data, title),
        "",
        "## Profil",
        "",
        profil,
        "",
        render_experiences(data, job_tags, title_weight, llm if llm and llm.used_llm else None),
        "",
        render_formations(data, job_tags),
        "",
        render_competences(data, job_tags),
        "",
        render_certifications(data),
        "",
    ]
    return "\n".join(parts)
