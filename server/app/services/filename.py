"""Extraction employeur + intitulé de poste depuis une fiche + nommage fichier."""

from __future__ import annotations

import re
import unicodedata
LABEL_RE = re.compile(
    r"(?:^|\n)\s*(?:entreprise|soci[eé]t[eé]|employeur|company|client|organisme|structure|employer|groupe|cabinet|agence)\s*[:\-–—]\s*([^\n|,;]{2,80})",
    re.IGNORECASE,
)

LABEL_INLINE_RE = re.compile(
    r"(?:^|\n)\s*(?:entreprise|soci[eé]t[eé]|employeur|company|groupe)\s+"
    r"([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ0-9][\wÀ-ÿ&.'’-]{1,40}"
    r"(?:\s+[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ0-9][\wÀ-ÿ&.'’-]{1,30}){0,3})\b"
)

ABOUT_KW_RE = re.compile(
    r"(?:rejoignez|rejoindre|rejoins|au sein (?:de|d['’])|chez|pour le compte (?:de|d['’])|"
    r"au sein d['’]?une?|"
    r"[aà]\s*propos\s+de)\s+",
    re.IGNORECASE,
)

COMPANY_NAME_RE = re.compile(
    r"^([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ0-9][\wÀ-ÿ&.'’-]{0,40}"
    r"(?:\s+(?:et|&|de|du|des|la|le)?\s*[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ0-9][\wÀ-ÿ&.'’-]{1,30}){0,4})"
)

RECRUTE_RE = re.compile(
    r"(?:^|\n)\s*([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ][\wÀ-ÿ&.'’-]{1,40}"
    r"(?:\s+[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ][\wÀ-ÿ&.'’-]{1,30}){0,3})\s+"
    r"(?:recrute|recherche|embauche)",
    re.IGNORECASE,
)

DASH_LINE_RE = re.compile(
    r"(?:^|\n)\s*([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ][\wÀ-ÿ&.'’-]{1,40}"
    r"(?:\s+[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ][\wÀ-ÿ&.'’-]{1,30}){0,3})\s*[\-–—]\s*"
    r"(?:CDI|CDD|Stage|Alternance|H\/F|F\/H)",
    re.IGNORECASE,
)

JOB_TITLE_LABEL_RE = re.compile(
    r"(?:^|\n)\s*(?:intitul[eé]\s*(?:du\s*)?poste|titre\s*(?:du\s*)?poste|poste|"
    r"job\s*title|position|r[oô]le)\s*[:\-–—]\s*([^\n]{3,100})",
    re.IGNORECASE,
)

JOB_TITLE_HF_RE = re.compile(
    r"(?:^|\n)\s*([^\n]{5,90}?)\s*(?:\((?:H\/F|F\/H|HF|M\/F)\)|(?:H\/F|F\/H))\s*(?:\n|$)",
    re.IGNORECASE,
)

JOB_TITLE_INLINE_RE = re.compile(
    r"(?:nous\s+(?:recherchons|cherchons)|recherche(?:ons)?)\s+(?:un[e]?\s+)?"
    r"([^\n.]{5,80}?)(?:\s+(?:pour|afin|qui)\b|[.!]|$)",
    re.IGNORECASE,
)

NOISE = frozenset(
    {
        "cdi",
        "cdd",
        "temps",
        "plein",
        "paris",
        "france",
        "remote",
        "hybride",
        "junior",
        "senior",
        "h/f",
        "hf",
        "f/h",
        "nous",
        "notre",
        "nos",
        "votre",
        "vos",
        "une",
        "un",
        "le",
        "la",
        "les",
        "des",
        "du",
        "poste",
        "offre",
        "emploi",
        "equipe",
        "équipes",
        "equipes",
        "team",
        "teams",
    }
)


def _strip_accents(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def slug_filename(name: str | None, *, max_len: int = 48) -> str:
    slug = _strip_accents(str(name or ""))
    slug = slug.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"^-|-$", "", slug)
    slug = slug[:max_len]
    slug = re.sub(r"-$", "", slug)
    return slug or ""


def extract_company(job_text: str | None, llm_company: str | None = None) -> str | None:
    """Récupère l'employeur : LLM d'abord, puis heuristiques multiples."""
    from_llm = _clean_company(llm_company)
    if from_llm:
        return from_llm

    text = str(job_text or "")
    candidates: list[str] = []

    labeled = LABEL_RE.search(text)
    if labeled:
        candidates.append(labeled.group(1))

    labeled_inline = LABEL_INLINE_RE.search(text)
    if labeled_inline:
        candidates.append(labeled_inline.group(1))

    recrute = RECRUTE_RE.search(text)
    if recrute:
        candidates.append(recrute.group(1))

    dash = DASH_LINE_RE.search(text)
    if dash:
        candidates.append(dash.group(1))

    about = _extract_about_company(text)
    if about:
        candidates.append(about)

    mail = re.search(r"@([a-z0-9-]+)\.(?:com|fr|io|co|net|org)\b", text, re.IGNORECASE)
    if mail and not re.search(r"gmail|outlook|hotmail|yahoo|proton", mail.group(1), re.IGNORECASE):
        candidates.append(_title_case_company(mail.group(1).replace("-", " ")))

    url = re.search(
        r"(?:https?://)?(?:www\.)?([a-z0-9-]+)\.(?:com|fr|io|co|net|org)\b",
        text,
        re.IGNORECASE,
    )
    if url and not re.search(
        r"linkedin|welcome|indeed|hellowork|google|github", url.group(1), re.IGNORECASE
    ):
        candidates.append(_title_case_company(url.group(1).replace("-", " ")))

    for raw in candidates:
        cleaned = _clean_company(raw)
        if cleaned:
            return cleaned
    return None


def extract_job_title(job_text: str | None) -> str | None:
    """Extrait l'intitulé de poste déclaré dans la fiche (si présent)."""
    text = str(job_text or "")

    labeled = JOB_TITLE_LABEL_RE.search(text)
    if labeled:
        title = _clean_job_title(labeled.group(1))
        if title:
            return title

    hf = JOB_TITLE_HF_RE.search(text)
    if hf:
        title = _clean_job_title(hf.group(1))
        if title:
            return title

    inline = JOB_TITLE_INLINE_RE.search(text)
    if inline and _looks_like_job_title(inline.group(1)):
        title = _clean_job_title(inline.group(1))
        if title:
            return title

    first = next(
        (
            line.strip()
            for line in text.split("\n")
            if 8 <= len(line.strip()) <= 80
        ),
        None,
    )
    if first and _looks_like_job_title(first) and not _looks_like_sentence(first):
        return _clean_job_title(first)
    return None


PERSON_SLUG = "lucas-schrever"


def build_job_export_filename(
    job_title: str | None,
    company: str | None,
    *,
    english: bool = False,
) -> str:
    """lucas-schrever-{poste}-{entreprise|defaut}-{fr|en}."""
    poste = slug_filename(job_title, max_len=48) or "cv"
    org = slug_filename(company, max_len=40) or ("default" if english else "defaut")
    lang = "en" if english else "fr"
    return f"{PERSON_SLUG}-{poste}-{org}-{lang}"


def _extract_about_company(text: str) -> str | None:
    for match in ABOUT_KW_RE.finditer(text):
        rest = text[match.end() :]
        name = COMPANY_NAME_RE.match(rest)
        if not name:
            continue
        cleaned = _clean_company(name.group(1))
        if cleaned:
            return cleaned
    return None


def _clean_company(raw: str | None) -> str | None:
    t = str(raw or "")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[|•·].*$", "", t)
    t = re.sub(r"\s*[-–—]\s*(cdi|cdd|stage|alternance|h/f|f/h).*$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t)
    t = re.sub(r"[.,;:!?]+$", "", t)
    t = t.strip()
    if not t or len(t) < 2 or len(t) > 80:
        return None

    if re.match(r"^(une?|des?|du|la|le|les|nos?|notre|votre|vos|cette?|cet)\b", t, re.IGNORECASE):
        return None
    if re.search(r"\b(équipe|equipes|équipes|teams?)\b", t, re.IGNORECASE) and not re.search(
        r"\b(SAS|SA|SARL|Inc|Ltd)\b", t, re.IGNORECASE
    ):
        return None

    norm = _strip_accents(t).lower()
    if norm in NOISE:
        return None
    if re.match(r"^(poste|offre|mission|profil|description|intitule|titre)$", t, re.IGNORECASE):
        return None
    if (
        re.match(
            r"^(developpeur|developer|ingenieur|ingénieur|chef|manager|expert|product|software)",
            t,
            re.IGNORECASE,
        )
        and len(t.split()) <= 3
    ):
        return None
    return t[:80]


def _clean_job_title(raw: str | None) -> str | None:
    t = str(raw or "")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s*\((?:H/F|F/H|HF|M/F)\)\s*", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(?:H/F|F/H|HF|M/F)\b", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*[-–—]\s*(CDI|CDD|Stage|Alternance).*$", "", t, flags=re.IGNORECASE)
    t = re.sub(r"[#*_`]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if not t or len(t) < 3 or len(t) > 90:
        return None
    if re.match(
        r"^(entreprise|societe|société|company|missions?|profil|description)",
        t,
        re.IGNORECASE,
    ):
        return None
    return t[:90]


def _looks_like_job_title(line: str) -> bool:
    return bool(
        re.search(
            r"developpeur|développeur|developer|engineer|ingénieur|chef de projet|"
            r"product owner|manager|consultant|expert|fullstack|full-stack|frontend|backend",
            line,
            re.IGNORECASE,
        )
    )


def _looks_like_sentence(line: str) -> bool:
    return bool(re.match(r"^(chez|nous|rejoignez|vous|notre|dans|pour|avec)\b", line, re.IGNORECASE)) or bool(
        re.search(r"[,.]", line)
    )


def _title_case_company(slug: str) -> str:
    return " ".join(
        w[0].upper() + w[1:].lower() if w else w
        for w in str(slug).split()
        if w
    )
