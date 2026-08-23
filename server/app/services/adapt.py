"""Adaptation d'un profil statique à une fiche de poste
(descriptif + compétences — expériences inchangées).
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.filename import extract_company, extract_job_title
from app.services.match import extract_job_skill_hints
from app.services.ollama import chat_json, check_ollama_status, llm_is_usable

PROFIL_TITLES = ["## Profil", "## Summary"]
SKILLS_TITLES = [
    "## Compétences techniques",
    "## Compétences",
    "## Technical skills",
    "## Skills",
]


async def adapt_profile_to_job(
    profile: dict[str, Any],
    job_text: str,
    *,
    english: bool = False,
    llm_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    markdown = str(profile.get("markdown") or "")
    profil_section = _extract_section(markdown, PROFIL_TITLES)
    skills_section = _extract_section(markdown, SKILLS_TITLES)
    job_title_detected = extract_job_title(job_text)
    company_heuristic = extract_company(job_text, None)
    profil_base = (
        (profil_section["body"] if profil_section else None)
        or profile.get("summary")
        or ""
    )
    skills_base = (skills_section["full"] if skills_section else None) or ""
    allowed_skills = _collect_allowed_skills(profile.get("keywords"), skills_base)
    overlap = _skill_overlap(job_text, allowed_skills)

    adapted: dict[str, Any]
    source = "local"
    fallback = False
    reason: str | None = None

    category = None
    if isinstance(profile.get("category"), dict):
        category = profile["category"].get("name")
    if not category:
        category = profile.get("category_name")

    status = llm_status if llm_status is not None else await check_ollama_status()

    if llm_is_usable(status):
        try:
            adapted = await _adapt_with_ollama(
                job_text=job_text,
                english=english,
                profile_name=profile.get("name"),
                profile_title=profile.get("title"),
                job_title_detected=job_title_detected,
                company_hint=company_heuristic,
                profil=profil_base,
                skills_markdown=skills_base,
                category=category,
                allowed_skills=allowed_skills,
                overlap=overlap,
            )
            source = "ollama"
            reason = adapted.get("reason") or None
        except Exception as exc:  # noqa: BLE001
            adapted = _adapt_locally(
                job_text=job_text,
                english=english,
                profil=profil_base,
                skills_markdown=skills_base,
                profile_title=profile.get("title"),
                profile_name=profile.get("name"),
                job_title_detected=job_title_detected,
            )
            source = "local"
            fallback = True
            reason = f"Adaptation locale — {exc}"
    else:
        adapted = _adapt_locally(
            job_text=job_text,
            english=english,
            profil=profil_base,
            skills_markdown=skills_base,
            profile_title=profile.get("title"),
            profile_name=profile.get("name"),
            job_title_detected=job_title_detected,
        )
        if status.get("enabled"):
            fallback = True
            reason = f"Adaptation locale — {status.get('message') or 'Ollama non prêt'}"
        else:
            reason = "Adaptation locale (Ollama désactivé)"

    company = extract_company(job_text, adapted.get("company")) or company_heuristic or None

    title = _clean_title(adapted.get("title")) or profile.get("title")
    if job_title_detected and (
        not title
        or _normalize_loose(title) == _normalize_loose(profile.get("title"))
        or _normalize_loose(title) == _normalize_loose(profile.get("name"))
    ):
        title = (
            _synthesize_title_locally(
                english=english,
                profile_title=profile.get("title"),
                profile_name=profile.get("name"),
                job_title_detected=job_title_detected,
                job_text=job_text,
                highlighted=overlap.get("highlighted") or [],
            )
            or title
        )

    next_md = markdown
    if adapted.get("profil"):
        next_md = _replace_section_body(next_md, PROFIL_TITLES, adapted["profil"])
    if adapted.get("skills_markdown"):
        skills = normalize_skills_markdown(adapted["skills_markdown"])
        next_md = _replace_section_full(next_md, SKILLS_TITLES, skills)
    if title:
        next_md = _replace_cv_role(next_md, title)

    return {
        "markdown": repair_cv_markdown_headings(next_md),
        "title": title or profile.get("title"),
        "summary": adapted.get("profil") or profile.get("summary"),
        "company": company,
        "job_title_detected": job_title_detected,
        "reason": reason,
        "source": source,
        "fallback": fallback,
        "added_skills": adapted.get("added_skills") or [],
        "skipped_skills": adapted.get("skipped_skills") or overlap.get("not_in_profile") or [],
        "message": (
            f"Profile adapted · {profile.get('name')}"
            if english
            else f"Profil adapté · {profile.get('name')}"
        ),
    }


async def _adapt_with_ollama(
    *,
    job_text: str,
    english: bool,
    profile_name: Any,
    profile_title: Any,
    job_title_detected: str | None = None,
    company_hint: str | None = None,
    profil: str,
    skills_markdown: str,
    category: Any,
    allowed_skills: list[str] | None = None,
    overlap: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    lang = "English" if english else "French"
    lang_rule = (
        "CRITICAL: title, profil, skills_markdown, skill_order, reason MUST be English only."
        if english
        else (
            "RÈGLE LANGUE ABSOLUE: title, profil, skills_markdown, skill_order et reason DOIVENT être en FRANÇAIS.\n"
            'Interdit: phrases anglaises du type "Experienced…", "Skilled…", "Proven track record…".\n'
            "Écris le profil à la 1ère personne (je) ou impersonnel professionnel FR."
        )
    )
    overlap = overlap or {"highlighted": [], "not_in_profile": []}
    allowed = allowed_skills or []

    system = f"""Tu adaptes un CV existant à UNE fiche de poste. Double fidélité :
- coller à l'offre (intitulé, missions, vocabulaire, stack qui matchent) ;
- rester vrai par rapport au CV (parcours, outils déjà listés). Pas d'invention.
{lang_rule}

Réponds en JSON strict :
{{
  "title": "<intitulé CV court, {lang}>",
  "company": "<employeur court si présent, sinon null>",
  "profil": "<2 à 3 phrases NOUVELLES en {lang}>",
  "skill_order": ["<compétence déjà dans allowed_skills, la plus pertinente en premier>"],
  "skills_markdown": "<même section ## / ### que current_skills_markdown, puces réordonnées>",
  "reason": "<1 phrase en {lang} : ce qui a été aligné sur l'offre>"
}}

Règles :
1) TITRE
   - Priorité à l'intitulé de l'offre (job.title / job_title_detected) s'il est crédible pour ce profil.
   - Tu peux reprendre 1 ou 2 termes de stack UNIQUEMENT s'ils sont dans overlap.highlighted.
   - Interdit d'ajouter un outil absent du CV. Max ~70 caractères.

2) COMPANY
   - Nom court visible dans l'offre (Chez X, X recrute, site X.com…). company_hint est un indice.
   - N'invente jamais. null si rien d'identifiable.

3) PROFIL (le plus important)
   - Réécris entièrement. Le texte de base ne doit PAS être recopié.
   - Écho aux missions de l'offre (interfaces, APIs, qualité, delivery…) seulement si le CV le justifie.
   - Intègre naturellement overlap.highlighted (pas une liste à puces).
   - overlap.not_in_profile : ne les présente JAMAIS comme maîtrisées. Une seule ouverture d'apprentissage est tolérée, sans en faire le cœur du pitch.
   - Pas d'expérience, client, diplôme ou outil inventés.

4) COMPÉTENCES
   - skill_order : 6 à 12 items pris EXCLUSIVEMENT dans allowed_skills, triés par pertinence pour CETTE offre.
   - skills_markdown : conserve les titres ### existants. Réordonne les puces (prioritaires en haut de chaque groupe).
   - Interdit d'ajouter une techno absente de current_skills_markdown / allowed_skills.
   - Ne supprime pas de compétences : descends-les si peu pertinentes.

5) Expériences : ne pas les modifier."""

    user = {
        "output_language": lang,
        "profile": {
            "name": profile_name,
            "title": profile_title,
            "category": category,
            "current_profil": profil,
            "current_skills_markdown": skills_markdown,
            "allowed_skills": allowed,
        },
        "job": {
            "title": job_title_detected,
            "company_hint": company_hint,
            "outline": _outline_job(job_text),
            "text": str(job_text)[:9000],
        },
        "overlap": {
            "highlighted": overlap.get("highlighted") or [],
            "not_in_profile": overlap.get("not_in_profile") or [],
        },
    }

    raw = await chat_json(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        temperature=0.28,
    )

    profil_base = str(profil or "").strip()
    skills_base = str(skills_markdown or "").strip()
    next_profil = str(raw.get("profil") or "").strip()
    title = _clean_title(raw.get("title")) or _synthesize_title_locally(
        english=english,
        profile_title=profile_title,
        profile_name=profile_name,
        job_title_detected=job_title_detected,
        job_text=job_text,
        highlighted=overlap.get("highlighted") or [],
    )

    if not english and next_profil and _looks_english(next_profil):
        next_profil = ""
    if english and next_profil and _looks_french(next_profil):
        next_profil = ""
    if not next_profil or _normalize_loose(next_profil) == _normalize_loose(profil_base):
        next_profil = _rewrite_profil_from_overlap(
            english=english,
            profile_title=title or profile_title,
            highlighted=overlap.get("highlighted") or [],
            job_text=job_text,
            fallback_profil=profil_base,
        )

    order = raw.get("skill_order") if isinstance(raw.get("skill_order"), list) else []
    order_names = [
        str(x).strip()
        for x in order
        if str(x).strip() and _is_allowed_skill(str(x), allowed)
    ]
    next_skills = _apply_skill_adaptation(
        original_md=skills_base,
        llm_md=str(raw.get("skills_markdown") or ""),
        allowed=allowed,
        skill_order=order_names,
        highlighted=overlap.get("highlighted") or [],
        english=english,
    )

    company_raw = raw.get("company")
    company = None
    if company_raw and str(company_raw).lower() != "null":
        company = str(company_raw).strip()

    return {
        "title": title,
        "company": company,
        "profil": next_profil,
        "skills_markdown": next_skills,
        "added_skills": order_names[:12],
        "skipped_skills": overlap.get("not_in_profile") or [],
        "reason": str(raw.get("reason") or "").strip() or None,
    }


def _normalize_loose(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").lower()).strip()


def _looks_english(text: str) -> bool:
    t = str(text or "").lower()
    en = len(
        re.findall(
            r"\b(the|with|and|experienced|skilled|proven|strong|focus|successful|development|manager|track|record|teams)\b",
            t,
        )
    )
    fr = len(
        re.findall(
            r"\b(je|j'ai|avec|dans|pour|une|des|expérience|compétences|équipe|projet|assure|intervient)\b",
            t,
        )
    )
    return en >= 3 and en > fr


def _looks_french(text: str) -> bool:
    t = str(text or "").lower()
    fr = len(
        re.findall(
            r"\b(je|j'ai|avec|dans|pour|expérience|compétences|équipe|projet|assure)\b",
            t,
        )
    )
    en = len(re.findall(r"\b(the|with|experienced|skilled|proven|strong)\b", t))
    return fr >= 2 and fr > en


def _rewrite_profil_locally(
    *,
    english: bool,
    profil: str,
    profile_title: Any,
    job_text: str,
) -> str:
    tokens = _extract_job_tokens(str(job_text or "").lower())[:5]
    focus = (
        ", ".join(tokens)
        if tokens
        else ("the target role" if english else "le poste visé")
    )
    role = profile_title or ("Professional" if english else "Professionnel")
    if english:
        return (
            f"{role} with hands-on delivery experience, I align my profile with {focus}. "
            "I emphasize coordination, execution quality and the skills most relevant to this "
            "offer while staying grounded in my real track record."
        )
    return (
        f"{role}, j'adapte mon positionnement à {focus}. "
        "Je mets en avant le cadrage, la livraison et les compétences les plus pertinentes "
        "pour cette offre, en m'appuyant sur mon parcours réel."
    )


def _collect_allowed_skills(keywords: Any, skills_markdown: str) -> list[str]:
    names: list[str] = []
    for raw in str(keywords or "").split(","):
        k = raw.strip()
        if k:
            names.append(k)
    for line in str(skills_markdown or "").splitlines():
        m = re.match(r"^\s*-\s+(.+)$", line)
        if m:
            names.append(m.group(1).strip())
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(name)
    return out


def _normalize_skill_key(name: str) -> str:
    s = re.sub(r"[^a-z0-9+.#]+", " ", str(name or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def _is_allowed_skill(name: str, allowed: list[str]) -> bool:
    needle = _normalize_skill_key(name)
    if len(needle) < 2:
        return False
    for raw in allowed:
        hay = _normalize_skill_key(raw)
        if not hay:
            continue
        if needle == hay or needle in hay or (len(needle) >= 4 and hay in needle):
            return True
    return False


def _outline_job(job_text: str) -> dict[str, str]:
    """Découpe l'offre par titres courts (missions, profil…) — pas de liste d'employeurs."""
    heading = re.compile(
        r"^(?:[\s•\-–—]*)(?:tes |ton |vos |votre |notre |nos |l['’])?"
        r"(missions?|profil|équipe|equipe|avantages?|prerequis|prérequis|"
        r"requirements?|responsibilities|about you|stack|technos?)\b",
        re.I,
    )
    blocks: dict[str, list[str]] = {"intro": []}
    current = "intro"
    for line in str(job_text or "").splitlines():
        stripped = line.strip()
        if stripped and len(stripped) <= 80 and heading.match(stripped):
            current = stripped[:70]
            blocks.setdefault(current, [])
            continue
        blocks.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in blocks.items() if "\n".join(v).strip()}


def _skill_overlap(job_text: str, allowed: list[str]) -> dict[str, list[str]]:
    job = str(job_text or "")
    highlighted: list[str] = []
    for name in allowed:
        key = _normalize_skill_key(name)
        if len(key) < 2:
            continue
        parts = [p.strip() for p in re.split(r"[,/]| — |\s+", name) if p.strip()]
        matched = _token_in_job(job.lower(), key) or any(
            _token_in_job(job.lower(), _normalize_skill_key(p))
            for p in parts
            if len(_normalize_skill_key(p)) >= 3
        )
        if matched:
            highlighted.append(name)
    seen: set[str] = set()
    uniq: list[str] = []
    for name in highlighted:
        k = _normalize_skill_key(name)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(name)

    not_in: list[str] = []
    for hint in extract_job_skill_hints(job):
        if _is_allowed_skill(hint, allowed):
            continue
        if _hint_looks_like_skill(hint, job):
            not_in.append(_normalize_skill_key(hint).strip(" ."))
    return {"highlighted": uniq[:16], "not_in_profile": not_in[:12]}


_HINT_NOISE = frozenset(
    {
        "tes",
        "ton",
        "nous",
        "notre",
        "vos",
        "cote",
        "pme",
        "esn",
        "cdi",
        "cdd",
        "missions",
        "profil",
        "equipe",
        "france",
        "ans",
        "web",
        "plus",
        "group",
        "full",
        "stack",
        "back",
        "front",
        "chez",
        "pour",
        "avec",
        "dans",
        "api",
    }
)


def _hint_looks_like_skill(hint: str, job_text: str) -> bool:
    h = _normalize_skill_key(hint).strip(" .")
    if len(h) < 3 or h in _HINT_NOISE:
        return False
    if re.search(
        rf"\b{re.escape(h)}\s+(group|groupe|sas|sarl|gmbh|inc|ltd)\b",
        job_text,
        re.I,
    ):
        return False
    if "." in h or "#" in h or "+" in h:
        return True
    for m in re.finditer(re.escape(h), job_text, re.I):
        orig = job_text[m.start() : m.end()]
        if orig.isupper() or (orig[:1].isupper() and len(orig) >= 3):
            return True
    return False


def _rewrite_profil_from_overlap(
    *,
    english: bool,
    profile_title: Any,
    highlighted: list[str],
    job_text: str,
    fallback_profil: str,
) -> str:
    """Pitch de secours à partir du recoupement offre/CV, sans inventer d'outils."""
    role = profile_title or ("Professional" if english else "Professionnel")
    focus = ", ".join(highlighted[:4]) if highlighted else ""
    if english:
        if focus:
            return (
                f"{role} delivering web products end to end, with a focus on {focus} "
                "where they match this role. I care about maintainable interfaces, solid APIs "
                "and code quality through to production."
            )
        return fallback_profil
    if focus:
        return (
            f"{role}, je conçois et livre des produits web de bout en bout, "
            f"en mettant en avant {focus} lorsque c'est pertinent pour le poste. "
            "Je soigne les interfaces, les APIs et la qualité de code jusqu'à la production."
        )
    return fallback_profil


def _apply_skill_adaptation(
    *,
    original_md: str,
    llm_md: str,
    allowed: list[str],
    skill_order: list[str],
    highlighted: list[str],
    english: bool,  # noqa: ARG001 — signature stable with callers
) -> str:
    base = normalize_skills_markdown(original_md)
    sanitized = _sanitize_llm_skills(llm_md, allowed)
    if sanitized:
        orig_n = len(re.findall(r"^\s*-\s+", original_md or "", re.M))
        new_n = len(re.findall(r"^\s*-\s+", sanitized, re.M))
        if orig_n == 0 or new_n >= max(3, int(0.55 * orig_n)):
            base = sanitized
    tokens = [_normalize_skill_key(n) for n in [*skill_order, *highlighted] if n]
    tokens = [t for t in tokens if t]
    merged = _reorder_skills_markdown(base, tokens) or base
    merged = _strip_offer_skills_section(merged)
    merged = _strip_pertinence_labels(merged)
    return normalize_skills_markdown(merged)


def _sanitize_llm_skills(llm_md: str, allowed: list[str]) -> str | None:
    md = normalize_skills_markdown(str(llm_md or "").strip())
    if not md or not re.search(r"^#{2,3}\s", md, re.M):
        return None
    out: list[str] = []
    kept = 0
    for line in md.splitlines():
        if re.match(r"^\s*-\s+", line):
            if _bullet_is_safe(line, allowed):
                out.append(line)
                kept += 1
            continue
        out.append(line)
    if kept < 3:
        return None
    return "\n".join(out).strip()


def _bullet_is_safe(line: str, allowed: list[str]) -> bool:
    text = re.sub(r"^\s*-\s+", "", line).strip()
    if not text:
        return False
    if _is_allowed_skill(text, allowed):
        return True
    parts = [p.strip() for p in re.split(r"[,/]| — | – ", text) if p.strip()]
    if not parts:
        return False
    ok = sum(1 for p in parts if _is_allowed_skill(p, allowed) or len(_normalize_skill_key(p)) < 3)
    return ok >= max(1, len(parts) - 1)


def _tokens_from_allowed(job_or_blob: str, allowed: list[str]) -> list[str]:
    blob = str(job_or_blob or "").lower()
    hits: list[str] = []
    for name in allowed:
        key = _normalize_skill_key(name)
        if len(key) >= 2 and (key in blob or _token_in_job(blob, key)):
            hits.append(key)
        for part in re.split(r"[,/]", name):
            pk = _normalize_skill_key(part)
            if len(pk) >= 2 and (pk in blob or _token_in_job(blob, pk)):
                hits.append(pk)
    return list(dict.fromkeys(hits))


def _filter_added_skills(
    added_skills: list[Any] | None,
    allowed: list[str],
    existing_md: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    existing = str(existing_md or "").lower()
    kept: list[dict[str, Any]] = []
    skipped: list[str] = []
    for item in added_skills or []:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            pertinence = item.get("pertinence")
        else:
            name = str(item or "").strip()
            pertinence = None
        if not name or len(name) < 2:
            continue
        if name.lower() in existing:
            continue
        if not _is_allowed_skill(name, allowed):
            skipped.append(name)
            continue
        kept.append({"name": name, "pertinence": pertinence})
    return kept, skipped


def _merge_added_skills(
    skills_markdown: str,
    added_skills: list[Any] | None,
    english: bool,
) -> str:
    """Intègre les skills de l'offre dans les ### existants."""
    md = _strip_offer_skills_section(str(skills_markdown or "").strip())
    md = _strip_pertinence_labels(md)

    items: list[dict[str, Any]] = []
    for item in added_skills or []:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            pertinence = item.get("pertinence")
        else:
            name = str(item or "").strip()
            pertinence = None
        if not name or len(name) < 2 or len(name) > 60:
            continue
        if name.lower() in md.lower():
            continue
        items.append(
            {
                "name": name,
                "score": _pertinence_score(pertinence),
                "line": f"- {name}",
            }
        )
    if not items:
        return md

    items.sort(key=lambda x: x["score"], reverse=True)

    if md:
        lines = re.split(r"\r?\n", md)
    else:
        lines = ["## Skills" if english else "## Compétences", ""]

    groups: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        if re.match(r"^###\s+", line.strip()):
            groups.append({"index": i, "header": line.strip()})

    for skill in items:
        target = _pick_skill_group(groups, skill["name"], english)
        if target:
            insert_at = target["index"] + 1
            while insert_at < len(lines) and lines[insert_at].strip() == "":
                insert_at += 1
            if skill["score"] >= 3:
                lines.insert(insert_at, skill["line"])
                for g in groups:
                    if g["index"] >= insert_at:
                        g["index"] += 1
            else:
                end = insert_at
                while end < len(lines) and not re.match(r"^#{2,3}\s", lines[end].strip()):
                    end += 1
                lines.insert(end, skill["line"])
                for g in groups:
                    if g["index"] >= end:
                        g["index"] += 1
        else:
            h = _guess_new_group_header(skill["name"], english)
            lines.extend(["", h, "", skill["line"]])
            groups.append({"index": len(lines) - 3, "header": h})

    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _strip_offer_skills_section(md: str) -> str:
    return re.sub(
        r"\n*###\s*(Issues de l'offre|From the job posting)\s*\n[\s\S]*?(?=\n##\s|\n###\s|$)",
        "\n",
        str(md or ""),
        flags=re.IGNORECASE,
    ).strip()


def _strip_pertinence_labels(md: str) -> str:
    s = re.sub(
        r"\s*[—\-–]\s*(pertinence|relevance)\s+(haute|moyenne|basse|high|medium|low)",
        "",
        str(md or ""),
        flags=re.IGNORECASE,
    )
    s = re.sub(r"[ \t]+\n", "\n", s)
    return s


def _pertinence_score(raw: Any) -> int:
    t = str(raw or "").lower()
    if re.search(r"high|haut", t):
        return 3
    if re.search(r"low|bas", t):
        return 1
    return 2


def _pick_skill_group(
    groups: list[dict[str, Any]],
    skill_name: str,
    english: bool,
) -> dict[str, Any] | None:
    if not groups:
        return None
    n = skill_name.lower()
    rules = [
        {
            "re": re.compile(
                r"scrum|agile|jira|kanban|waterfall|cascade|planning|backlog|stakeholder|pilotage|management|product owner|recette|specs"
            ),
            "headers": re.compile(r"pilotage|management|project|agile|scrum", re.I),
        },
        {
            "re": re.compile(r"figma|ux|ui|design|seo|semrush|pardot"),
            "headers": re.compile(r"design|ux|ui|seo", re.I),
        },
        {
            "re": re.compile(
                r"react|vue|angular|html|css|javascript|typescript|next|tailwind|wordpress|php|front"
            ),
            "headers": re.compile(r"front|web|design|complémentaire|complementary", re.I),
        },
        {
            "re": re.compile(r"node|nest|\.net|dotnet|c#|api|java|python|express|back"),
            "headers": re.compile(r"back|api|server|runtime", re.I),
        },
        {
            "re": re.compile(r"owasp|jwt|auth|sécurité|securite|security"),
            "headers": re.compile(r"back|sécu|security|outils|tools|pratiques|practices", re.I),
        },
        {
            "re": re.compile(r"jest|vitest|git|docker|ci/cd|github|test"),
            "headers": re.compile(r"outils|tools|devops|data", re.I),
        },
        {
            "re": re.compile(r"dor|dod|raid|raci|recette|uat|cadrage|backlog"),
            "headers": re.compile(r"pratiques|practices|pilotage|delivery", re.I),
        },
        {
            "re": re.compile(r"mongo|sql|postgres|data"),
            "headers": re.compile(r"data|devops|back", re.I),
        },
        {
            "re": re.compile(r"docker|kubernetes|aws|azure|ci/cd|devops|github"),
            "headers": re.compile(r"devops|data|ops|delivery|ingénierie|engineering", re.I),
        },
        {
            "re": re.compile(r"salesforce|pardot|crm|marketing"),
            "headers": re.compile(r"web|complémentaire|complementary|design|seo", re.I),
        },
    ]
    for rule in rules:
        if not rule["re"].search(n):
            continue
        hit = next((g for g in groups if rule["headers"].search(g["header"])), None)
        if hit:
            return hit
    return groups[-1]


def _guess_new_group_header(skill_name: str, english: bool) -> str:
    n = skill_name.lower()
    if re.search(r"react|vue|html|css|front|wordpress|prestashop|php", n):
        return "### Front-end"
    if re.search(r"node|nest|\.net|api|back|owasp", n):
        return "### Back-end"
    if re.search(r"mongo|sql|postgres", n):
        return "### Data"
    if re.search(r"docker|aws|devops|kubernetes|jest|git", n):
        return "### Tools" if english else "### Outils"
    if re.search(r"scrum|agile|jira|planning|raid|raci", n):
        return "### Delivery" if english else "### Pilotage"
    return "### Tools" if english else "### Outils"


def _adapt_locally(
    *,
    job_text: str,
    english: bool,
    profil: str,
    skills_markdown: str,
    profile_title: Any,
    profile_name: Any,
    job_title_detected: str | None = None,
) -> dict[str, Any]:
    """Fallback sans LLM : titre + réordonnancement des skills existantes. Pas d'invention."""
    allowed = _collect_allowed_skills(None, skills_markdown)
    tokens = _tokens_from_allowed(job_text, allowed) or _extract_job_tokens(
        str(job_text or "").lower()
    )
    skills = _reorder_skills_markdown(skills_markdown, tokens) or skills_markdown
    skills = normalize_skills_markdown(skills)

    generic_title = _synthesize_title_locally(
        english=english,
        profile_title=profile_title,
        profile_name=profile_name,
        job_title_detected=job_title_detected,
        job_text=job_text,
        highlighted=_skill_overlap(job_text, allowed).get("highlighted") or [],
    )

    return {
        "title": generic_title,
        "company": extract_company(job_text, None),
        "profil": str(profil or "").strip(),
        "skills_markdown": skills,
        "added_skills": [],
        "skipped_skills": [],
        "reason": (
            "Local adaptation (title + skill order, profile kept)"
            if english
            else "Adaptation locale (titre et ordre des compétences, descriptif conservé)"
        ),
    }


def _synthesize_title_locally(
    *,
    english: bool,
    profile_title: Any,
    profile_name: Any,
    job_title_detected: str | None,
    job_text: str,
    highlighted: list[str] | None = None,
) -> str | None:
    """Titre CV = interprétation entre intitulé fiche et profil."""
    job_title = (
        _clean_title(job_title_detected)
        or _clean_title(extract_job_title(job_text))
        or None
    )
    inferred = _infer_generic_title(str(job_text or "").lower(), english)
    profile = _clean_title(profile_title) or _clean_title(profile_name) or profile_title

    if job_title and highlighted:
        jt_norm = _normalize_loose(job_title)
        if any(
            (k := _normalize_skill_key(h)) and len(k) >= 4 and k in jt_norm
            for h in highlighted
        ):
            return job_title

    if not job_title:
        return inferred or profile

    jt = job_title.lower()
    pt = str(profile or "").lower()

    if (
        (re.search(r"(product\s*owner|\bpo\b)", jt) and re.search(r"projet|product|owner|manager|digital", pt))
        or (re.search(r"(chef de projet|project manager)", jt) and re.search(r"projet|manager|digital|product", pt))
        or (
            re.search(r"(developpeur|développeur|developer|fullstack|engineer|ingénieur)", jt)
            and re.search(r"(developpeur|développeur|fullstack|engineer|software)", pt)
        )
        or (
            re.search(r"(cyber|securite|sécurité|security)", jt)
            and re.search(r"(cyber|securite|sécurité|security|expert)", pt)
        )
    ):
        return job_title

    if re.search(r"product\s*owner", jt) and re.search(r"chef de projet|project manager", pt):
        return "Product Owner"
    if re.search(r"chef de projet", jt) and re.search(r"product owner", pt):
        return "Digital project manager" if english else "Chef de projet digital"

    return inferred or job_title or profile


def _prettify_token(t: str) -> str:
    mapping = {
        "next.js": "Next.js",
        "nextjs": "Next.js",
        "node.js": "Node.js",
        "node": "Node.js",
        "nestjs": "NestJS",
        ".net": ".NET",
        "dotnet": ".NET",
        "c#": "C#",
        "csharp": "C#",
        "react": "React",
        "typescript": "TypeScript",
        "javascript": "JavaScript",
        "mongodb": "MongoDB",
        "docker": "Docker",
        "figma": "Figma",
        "scrum": "Scrum",
        "agile": "Agile",
        "seo": "SEO",
        "wordpress": "WordPress",
    }
    return mapping.get(t) or (t[:1].upper() + t[1:] if t else t)


def _infer_generic_title(job_lower: str, english: bool) -> str | None:
    if re.search(r"product\s*owner|\bpo\b", job_lower):
        return "Product Owner"
    if re.search(r"software\s*engineer|ingénieur\s+logiciel|ingénieur\s+études", job_lower):
        return "Software Engineer"
    if re.search(r"chef\s+de\s+projet\s+web|project\s+manager\s+web", job_lower):
        return "Web project manager" if english else "Chef de projet web"
    if re.search(r"chef\s+de\s+projet|project\s+manager", job_lower):
        return "Digital project manager" if english else "Chef de projet digital"
    if re.search(r"cyber|sécurité|security|owasp|devsecops", job_lower):
        return "Application security expert" if english else "Expert cybersécurité applicative"
    if re.search(r"fullstack|full-stack|full\s*stack|développeur|developer|front|back", job_lower):
        return "Full-stack developer" if english else "Développeur Fullstack"
    return None


def _extract_job_tokens(job_lower: str) -> list[str]:
    known = [
        "react",
        "next.js",
        "nextjs",
        "vue",
        "angular",
        "typescript",
        "javascript",
        "node.js",
        "nodejs",
        "node",
        "nestjs",
        "express",
        ".net",
        "dotnet",
        "c#",
        "csharp",
        "python",
        "java",
        "php",
        "wordpress",
        "mongodb",
        "postgresql",
        "sql",
        "docker",
        "kubernetes",
        "aws",
        "azure",
        "scrum",
        "agile",
        "figma",
        "seo",
        "ux",
        "ui",
        "owasp",
        "devops",
        "ci/cd",
        "graphql",
        "rest",
        "api",
        "tailwind",
        "pardot",
        "salesforce",
        "jira",
        "kanban",
    ]
    hits = [k for k in known if _token_in_job(job_lower, k)]
    return list(dict.fromkeys(hits))[:12]


def _token_in_job(job_lower: str, token: str) -> bool:
    raw = str(token or "").lower()
    if not raw:
        return False
    if len(raw) <= 3 or raw in {".net", "node", "java", "net"}:
        escaped = re.escape(raw)
        return bool(re.search(rf"(?:^|[^a-z0-9]){escaped}(?:[^a-z0-9]|$)", job_lower, re.I))
    return raw in job_lower or raw.replace(".", "") in job_lower


def _reorder_skills_markdown(skills_markdown: str, tokens: list[str]) -> str | None:
    normalized = normalize_skills_markdown(skills_markdown)
    if not normalized or not tokens:
        return normalized
    lines = re.split(r"\r?\n", str(normalized))
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in lines:
        if re.match(r"^#{2,3}\s", line):
            if current:
                blocks.append(current)
            current = {"header": line, "items": []}
        elif current and re.match(r"^\s*-\s+", line):
            current["items"].append(line)
        elif current:
            current["items"].append(line)
        else:
            blocks.append({"header": line, "items": []})
    if current:
        blocks.append(current)

    def score_line(line: str) -> int:
        low = line.lower()
        return sum(1 for t in tokens if t in low)

    def score_block(block: dict[str, Any]) -> int:
        return sum(score_line(x) for x in block.get("items") or [])

    h2 = [b for b in blocks if str(b.get("header") or "").startswith("## ")]
    h3 = [b for b in blocks if str(b.get("header") or "").startswith("###")]
    rest = [b for b in blocks if b not in h2 and b not in h3]
    h3.sort(key=score_block, reverse=True)

    out: list[str] = []
    for b in h2 + h3 + rest:
        if b.get("header"):
            out.append(b["header"])
        items = [l for l in b["items"] if re.match(r"^\s*-\s+", l)]
        other = [l for l in b["items"] if not re.match(r"^\s*-\s+", l)]
        items.sort(key=score_line, reverse=True)
        out.extend(items)
        out.extend(other)
    return normalize_skills_markdown("\n".join(out))


def normalize_skills_markdown(raw: str | None) -> str:
    """Corrige les ### collés aux puces (bug fréquent Ollama / Pandoc)."""
    s = str(raw or "").replace("\r\n", "\n").strip()
    if not s:
        return s

    s = re.sub(r"([^\n#])\s*(#{2,3})\s+", r"\1\n\n\2 ", s)
    s = re.sub(r"(-\s[^\n]*?)\s*(#{2,3})\s+", r"\1\n\n\2 ", s)
    s = re.sub(r"(#{2,3}\s+[^\n]+?)\s*(-\s+)", r"\1\n\2", s)
    s = re.sub(r"\n{3,}", "\n\n", s)

    lines = []
    for line in s.split("\n"):
        t = line.rstrip()
        trimmed = t.strip()
        if re.match(r"^#{2,3}\s+\S", trimmed):
            lines.append(trimmed)
        elif re.match(r"^-\s+", trimmed):
            lines.append(f"- {re.sub(r'^-\s+', '', trimmed)}")
        else:
            lines.append(t)
    return "\n".join(lines).strip()


def _extract_section(markdown: str, titles: list[str]) -> dict[str, Any] | None:
    md = str(markdown or "")
    for title in titles:
        pattern = re.compile(
            rf"(^|\n)({_escape_re(title)})\s*\n([\s\S]*?)(?=\n##\s|\n</div>|$)",
            re.IGNORECASE,
        )
        m = pattern.search(md)
        if m:
            return {
                "title": m.group(2),
                "body": m.group(3).strip(),
                "full": f"{m.group(2)}\n\n{m.group(3).strip()}",
                "index": m.start() + (len(m.group(1)) if m.group(1) else 0),
            }
    return None


def _replace_section_body(markdown: str, titles: list[str], new_body: str) -> str:
    md = str(markdown or "")
    body = str(new_body).strip()
    for title in titles:
        pattern = re.compile(
            rf"((?:^|\n)({_escape_re(title)})\s*\n)([\s\S]*?)(?=\n##\s|\n</div>|$)",
            re.IGNORECASE,
        )
        if pattern.search(md):
            return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n", md, count=1)
    return md


def _replace_section_full(markdown: str, titles: list[str], new_full: str) -> str:
    md = str(markdown or "")
    block = str(new_full).strip()
    for title in titles:
        pattern = re.compile(
            rf"(^|\n)({_escape_re(title)})\s*\n[\s\S]*?(?=\n##\s|\n</div>|$)",
            re.IGNORECASE,
        )
        if pattern.search(md):
            return pattern.sub(lambda m: f"{m.group(1)}{block}\n", md, count=1)

    insert_before = re.search(r"\n## (Certifications|Langues|Languages)\b", md, re.IGNORECASE)
    if insert_before:
        idx = insert_before.start()
        return f"{md[:idx]}\n\n{block}\n{md[idx:]}"
    return f"{md.rstrip()}\n\n{block}\n"


def _replace_cv_role(markdown: str, title: str) -> str:
    return re.sub(
        r'(<p class="cv-role">)([\s\S]*?)(</p>)',
        lambda m: f"{m.group(1)}{_escape_html(title)}{m.group(3)}",
        str(markdown or ""),
        count=1,
        flags=re.IGNORECASE,
    )


def _clean_title(raw: Any) -> str | None:
    t = str(raw or "")
    t = re.sub(r"[#*_`]", "", t)
    t = re.sub(r"\s+", " ", t).strip()

    def _strip_tech_tail(m: re.Match[str]) -> str:
        return "" if re.search(r"react|node|\.net|vue|angular|typescript|java", m.group(0), re.I) else m.group(0)

    t = re.sub(r"\s*[\-–—|:]\s*.+$", _strip_tech_tail, t)
    t = re.sub(r"\s*\([^)]*(react|node|\.net|vue)[^)]*\)\s*$", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    if not t or len(t) > 60:
        return None
    return t


def _escape_re(s: str) -> str:
    return re.escape(s)


def _escape_html(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def repair_cv_markdown_headings(markdown: str) -> str:
    """Répare les ### collés aux puces dans tout le markdown CV."""
    md = str(markdown or "")
    md = re.sub(r"([^\n#])\s*(#{2,3})\s+", r"\1\n\n\2 ", md)
    md = re.sub(r"(#{2,3}\s+[^\n]+?)\s*(-\s+)", r"\1\n\2", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md
