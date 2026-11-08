"""Fetch and parse chapter HTML from known novel sources.

The LLM/job path is unchanged: this module only returns title + body (+ next URL).
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Callable

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

NOVEL18_RE = re.compile(
    r"^https?://(?:www\.)?novel18\.syosetu\.com/(n[0-9a-z]+)/(\d+)/?$",
    re.I,
)
NOVEL18_WORK_RE = re.compile(
    r"^https?://(?:www\.)?novel18\.syosetu\.com/(n[0-9a-z]+)/?$",
    re.I,
)


class AgeGateError(Exception):
    pass


class ScrapeError(Exception):
    pass


_VOID = frozenset(
    {"br", "img", "hr", "meta", "input", "link", "area", "base", "col", "embed", "source", "track", "wbr"}
)


class _NarouParser(HTMLParser):
    """Pull title and js-novel-text blocks out of current Narou chapter HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.blocks: list[list[str]] = []
        self.seen_body = False
        self._title_depth = 0
        self._block_depth = 0
        self._p_depth = 0
        self._skip_rt = 0
        self._cur_p: list[str] = []
        self._cur_block: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = set()
        for k, v in attrs:
            if k == "class" and v:
                classes.update(v.split())
        if "p-novel__body" in classes:
            self.seen_body = True
        if tag in _VOID:
            if self._p_depth:
                self._cur_p.append("\n")
            return
        if self._skip_rt:
            self._skip_rt += 1
            return
        if tag in ("rt", "rp"):
            self._skip_rt = 1
            return
        if self._title_depth:
            self._title_depth += 1
        elif "p-novel__title" in classes and not self.title_parts:
            self._title_depth = 1
        if self._block_depth:
            self._block_depth += 1
            if tag == "p" and self._p_depth == 0:
                self._p_depth = 1
                self._cur_p = []
            elif self._p_depth:
                self._p_depth += 1
        elif "js-novel-text" in classes:
            self._block_depth = 1
            self._cur_block = []

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID:
            return
        if self._skip_rt:
            self._skip_rt -= 1
            return
        if tag in ("rt", "rp") and self._skip_rt:
            return
        if self._p_depth:
            self._p_depth -= 1
            if self._p_depth == 0 and self._cur_block is not None:
                self._cur_block.append("".join(self._cur_p).replace("\xa0", " ").strip())
        if self._block_depth:
            self._block_depth -= 1
            if self._block_depth == 0 and self._cur_block is not None:
                self.blocks.append(self._cur_block)
                self._cur_block = None
        if self._title_depth:
            self._title_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_rt:
            return
        if self._title_depth:
            self.title_parts.append(data)
        elif self._p_depth:
            self._cur_p.append(data)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # <br/> etc. — do not change depth.
        self.handle_starttag(tag, attrs)


def _parse_novel18_html(html: str) -> tuple[str, str, bool]:
    parser = _NarouParser()
    parser.feed(html)
    parser.close()
    title = re.sub(r"\s+", " ", "".join(parser.title_parts)).strip()
    sections: list[str] = []
    for block in parser.blocks:
        text = "\n".join(block).strip()
        if text:
            sections.append(text)
    body = "\n\n——\n\n".join(sections)
    return title, body, parser.seen_body


def _is_age_gate(html: str, seen_body: bool) -> bool:
    if not html:
        return False
    if seen_body or "p-novel__title" in html:
        return False
    return "年齢確認" in html or "18歳未満" in html


def _is_confirm_url(url: str) -> bool:
    u = url.lower()
    return "over18" in u or "over18confirm" in u


def _fetch(url: str) -> tuple[int, str, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Cookie": "over18=yes",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ja,en;q=0.8",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            html = raw.decode(charset, errors="replace")
            return resp.status, html, resp.geturl()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return 404, "", url
        raise ScrapeError(f"HTTP {e.code} fetching {url}") from e
    except urllib.error.URLError as e:
        reason = e.reason if e.reason else e
        raise ScrapeError(f"network error fetching {url}: {reason}") from e


def _normalize_novel18(url: str) -> tuple[str, str, int]:
    raw = url.strip()
    m = NOVEL18_RE.match(raw) or NOVEL18_RE.match(raw.rstrip("/") + "/")
    if not m:
        raise ValueError(
            "URL must look like https://novel18.syosetu.com/<ncode>/<chapter>/"
        )
    ncode = m.group(1).lower()
    n = int(m.group(2))
    return f"https://novel18.syosetu.com/{ncode}/{n}/", ncode, n


def normalize_novel18_work(url: str) -> tuple[str, str, str]:
    """Accept a TOC or chapter URL. Return (work_url, ncode, first_chapter_url)."""
    raw = url.strip()
    ch = NOVEL18_RE.match(raw) or NOVEL18_RE.match(raw.rstrip("/") + "/")
    if ch:
        ncode = ch.group(1).lower()
        work_url = f"https://novel18.syosetu.com/{ncode}/"
        return work_url, ncode, f"{work_url}1/"
    wk = NOVEL18_WORK_RE.match(raw) or NOVEL18_WORK_RE.match(raw.rstrip("/") + "/")
    if not wk:
        raise ValueError(
            "URL must look like https://novel18.syosetu.com/<ncode>/"
        )
    ncode = wk.group(1).lower()
    work_url = f"https://novel18.syosetu.com/{ncode}/"
    return work_url, ncode, f"{work_url}1/"


def novel18_work_url_from(*urls: str) -> str:
    for u in urls:
        if not (u or "").strip():
            continue
        try:
            work_url, _, _ = normalize_novel18_work(u)
            return work_url
        except ValueError:
            continue
    return ""


def scrape_novel18_work(url: str) -> dict:
    work_url, _ncode, first_chapter_url = normalize_novel18_work(url)
    status, html, final = _fetch(work_url)
    title, _body, seen_body = _parse_novel18_html(html) if html else ("", "", False)
    if _is_confirm_url(final) or _is_age_gate(html, seen_body):
        status, html, final = _fetch(work_url)
        title, _body, seen_body = _parse_novel18_html(html) if html else ("", "", False)
        if _is_confirm_url(final) or _is_age_gate(html, seen_body):
            raise AgeGateError("novel18 age verification still showing (over18 cookie rejected)")
    if status == 404:
        raise ScrapeError(f"work page not found: {work_url}")
    title = title.strip()
    if not title:
        raise ValueError("could not read work title from URL (p-novel__title)")
    return {
        "title": title,
        "work_url": work_url,
        "first_chapter_url": first_chapter_url,
    }


def scrape_novel18(url: str) -> dict:
    chapter_url, ncode, n = _normalize_novel18(url)
    status, html, final = _fetch(chapter_url)
    title, body, seen_body = _parse_novel18_html(html) if html else ("", "", False)
    if _is_confirm_url(final) or _is_age_gate(html, seen_body):
        status, html, final = _fetch(chapter_url)
        title, body, seen_body = _parse_novel18_html(html) if html else ("", "", False)
        if _is_confirm_url(final) or _is_age_gate(html, seen_body):
            raise AgeGateError("novel18 age verification still showing (over18 cookie rejected)")
    if status == 404:
        return {"empty": True, "title": "", "body": "", "next_url": None}
    if not title and not body:
        return {"empty": True, "title": "", "body": "", "next_url": None}
    return {
        "empty": False,
        "title": title,
        "body": body,
        "next_url": f"https://novel18.syosetu.com/{ncode}/{n + 1}/",
    }


SOURCES: dict[str, Callable[[str], dict]] = {
    "novel18": scrape_novel18,
}

WORK_SOURCES: dict[str, Callable[[str], dict]] = {
    "novel18": scrape_novel18_work,
}


def scrape(source: str, url: str) -> dict:
    fn = SOURCES.get(source)
    if fn is None:
        known = ", ".join(sorted(SOURCES))
        raise ValueError(f"unknown source '{source}'. known: {known}")
    return fn(url)


def scrape_work(source: str, url: str) -> dict:
    fn = WORK_SOURCES.get(source)
    if fn is None:
        known = ", ".join(sorted(WORK_SOURCES))
        raise ValueError(f"unknown source '{source}'. known: {known}")
    return fn(url)
