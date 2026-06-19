"""Chargement d'une fiche de poste : URL ou texte brut."""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

URL_PATTERN = re.compile(r"^https?://\S+$", re.IGNORECASE)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip = False
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            text = data.strip()
            if text:
                self._chunks.append(text + " ")

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "".join(self._chunks))


def html_to_text(html: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return parser.text()


def _fetch_with_urllib(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def _fetch_with_playwright(url: str) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto(url, wait_until="domcontentloaded", timeout=90_000)
        page.wait_for_timeout(2_500)
        text = page.inner_text("body")
        browser.close()
        return text


def fetch_url(url: str) -> str:
    """Récupère le texte visible d'une URL (Playwright puis repli HTTP)."""
    errors: list[str] = []
    try:
        return _fetch_with_playwright(url)
    except Exception as exc:
        errors.append(f"playwright: {exc}")

    try:
        html = _fetch_with_urllib(url)
        text = html_to_text(html)
        if len(text.strip()) < 200:
            raise ValueError("contenu trop court après extraction HTML")
        return text
    except Exception as exc:
        errors.append(f"http: {exc}")

    raise RuntimeError(
        "Impossible de récupérer l'offre depuis l'URL. "
        "Collez le texte de l'offre dans le fichier jobs/*.txt\n"
        + "\n".join(errors)
    )


def extract_url_from_content(content: str) -> str | None:
    for line in content.splitlines():
        candidate = line.strip()
        if URL_PATTERN.match(candidate):
            return candidate
    stripped = content.strip()
    if URL_PATTERN.match(stripped):
        return stripped
    return None


def load_job_text(path: Path) -> tuple[str, str]:
    """
    Retourne (texte_brut, source).
    source = 'url' | 'text'
    """
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Fichier vide : {path}")

    url = extract_url_from_content(content)
    if url:
        return fetch_url(url), "url"

    return content, "text"
