"""Minimal EPUB 3 builder. Stdlib only: zipfile + XML escaping."""
from __future__ import annotations

import io
import uuid
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape

CONTAINER_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def _body_xhtml(text: str) -> str:
    """Escape text; each original newline becomes a hard break. No <p>."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return escape(text).replace("\n", "<br/>")


def _chapter_xhtml(title: str, body: str) -> str:
    t = escape(title)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh" lang="zh">\n'
        "<head>\n"
        f"<title>{t}</title>\n"
        '<meta charset="utf-8"/>\n'
        "<style>h1{margin:1.5em 0 1em 0;}</style>\n"
        "</head>\n"
        "<body>\n"
        f"<h1>{t}</h1>\n"
        f'<div class="chapter-body">{_body_xhtml(body)}</div>\n'
        "</body>\n"
        "</html>\n"
    )


def _nav_xhtml(book_title: str, items: list[tuple[str, str]]) -> str:
    lis = "\n".join(
        f'      <li><a href="{escape(href)}">{escape(title)}</a></li>'
        for href, title in items
    )
    if not lis:
        lis = "      <li>（没有章节）</li>"
    t = escape(book_title)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="zh" lang="zh">\n'
        "<head>\n"
        f"<title>{t}</title>\n"
        '<meta charset="utf-8"/>\n'
        "</head>\n"
        "<body>\n"
        '<nav epub:type="toc" id="toc">\n'
        "<h1>目录</h1>\n"
        f"<ol>\n{lis}\n    </ol>\n"
        "</nav>\n"
        "</body>\n"
        "</html>\n"
    )


def _package_opf(book_title: str, uid: str, modified: str, n: int) -> str:
    manifest_ch = "\n".join(
        f'    <item id="ch{i:04d}" href="ch{i:04d}.xhtml" '
        'media-type="application/xhtml+xml"/>'
        for i in range(1, n + 1)
    )
    spine = "\n".join(
        f'    <itemref idref="ch{i:04d}"/>' for i in range(1, n + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        'unique-identifier="pub-id" xml:lang="zh">\n'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f'    <dc:identifier id="pub-id">urn:uuid:{uid}</dc:identifier>\n'
        f"    <dc:title>{escape(book_title)}</dc:title>\n"
        "    <dc:language>zh</dc:language>\n"
        f'    <meta property="dcterms:modified">{modified}</meta>\n'
        "</metadata>\n"
        "<manifest>\n"
        '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" '
        'properties="nav"/>\n'
        f"{manifest_ch}\n"
        "</manifest>\n"
        "<spine>\n"
        f"{spine}\n"
        "</spine>\n"
        "</package>\n"
    )


def build_epub(title: str, chapters: list[tuple[str, str]]) -> bytes:
    """chapters: list of (title, body). Returns EPUB bytes."""
    uid = str(uuid.uuid4())
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    nav_items = [(f"ch{i:04d}.xhtml", ch_title) for i, (ch_title, _) in enumerate(chapters, 1)]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        mime = zipfile.ZipInfo("mimetype")
        mime.compress_type = zipfile.ZIP_STORED
        mime.extra = b""
        zf.writestr(mime, b"application/epub+zip")
        zf.writestr("META-INF/container.xml", CONTAINER_XML.encode("utf-8"))
        zf.writestr(
            "EPUB/package.opf",
            _package_opf(title, uid, modified, len(chapters)).encode("utf-8"),
        )
        zf.writestr("EPUB/nav.xhtml", _nav_xhtml(title, nav_items).encode("utf-8"))
        for i, (ch_title, body) in enumerate(chapters, 1):
            zf.writestr(
                f"EPUB/ch{i:04d}.xhtml",
                _chapter_xhtml(ch_title, body).encode("utf-8"),
            )
    return buf.getvalue()
