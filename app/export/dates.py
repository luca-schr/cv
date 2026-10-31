"""Mois en toutes lettres si la ligne du poste a la place, sinon abrégés."""

from __future__ import annotations

import re

# (forme courte, forme longue) — la courte se termine par un point quand elle est abrégée
_MONTHS = (
    ("janv.", "janvier"),
    ("févr.", "février"),
    ("avr.", "avril"),
    ("juil.", "juillet"),
    ("sept.", "septembre"),
    ("oct.", "octobre"),
    ("nov.", "novembre"),
    ("déc.", "décembre"),
    ("jan.", "january"),
    ("feb.", "february"),
    ("mar.", "march"),
    ("apr.", "april"),
    ("jun.", "june"),
    ("jul.", "july"),
    ("aug.", "august"),
    ("sep.", "september"),
    ("oct.", "october"),
    ("nov.", "november"),
    ("dec.", "december"),
)


def _match_case(source: str, target: str) -> str:
    if source[:1].isupper():
        return target[:1].upper() + target[1:]
    return target


def _apply(inner: str, *, full: bool) -> str:
    pairs = sorted(_MONTHS, key=lambda pair: len(pair[0 if full else 1]), reverse=True)
    for short, long in pairs:
        src, dst = (short, long) if full else (long, short)
        pattern = re.compile(rf"(?<![\w.]){re.escape(src)}(?![\w])", re.IGNORECASE)

        def repl(match: re.Match[str], dst: str = dst) -> str:
            return _match_case(match.group(0), dst)

        inner = pattern.sub(repl, inner)
    return inner


def _map_spans(markdown: str, *, full: bool) -> str:
    def repl(match: re.Match[str]) -> str:
        return f'<span class="cv-dates">{_apply(match.group(1), full=full)}</span>'

    return re.sub(r'<span class="cv-dates">([^<]*)</span>', repl, markdown)


def expand_months(markdown: str) -> str:
    return _map_spans(markdown, full=True)


def abbreviate_months(markdown: str) -> str:
    return _map_spans(markdown, full=False)


def dates_fit(html: str, stylesheets: list, *, base_url: str) -> bool:
    """Vrai si chaque date tient sur la ligne de son titre, sans dépasser."""
    from weasyprint import HTML

    document = HTML(string=html, base_url=base_url).render(stylesheets=stylesheets)
    fits = True

    def walk(box, heading=None) -> None:
        nonlocal fits
        if not fits:
            return
        element = getattr(box, "element", None)
        tag = getattr(element, "tag", None) if element is not None else None
        classes = ""
        if element is not None and hasattr(element, "get"):
            classes = element.get("class") or ""
        current = box if tag == "h3" else heading
        if "cv-dates" in classes.split():
            if current is None:
                fits = False
            else:
                right = box.position_x + box.width
                limit = current.position_x + current.width + 0.8
                if right > limit or current.height > box.height * 1.45:
                    fits = False
        for child in getattr(box, "children", []) or []:
            walk(child, current)

    for page in document.pages:
        walk(page._page_box)
    return fits
