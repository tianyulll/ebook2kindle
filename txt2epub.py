from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from ebooklib import epub
from typing import Callable, Optional

import uuid
import html
import re
import os
import tempfile


@dataclass
class EpubResult:
    input_txt: Path
    output_epub: Path
    encoding: str
    language: str

def detect_encoding(path: Path, sample_bytes: int = 200_000) -> str:
    raw = path.read_bytes()
    sample = raw[:sample_bytes]

    # Detect encoding from samples text
    try:
        from charset_normalizer import from_bytes  # optional dependency
        result = from_bytes(sample).best()
        if result and result.encoding:
            return result.encoding
    except Exception:
        pass

    # Heuristics
    if sample.startswith(b"\xff\xfe") or sample.startswith(b"\xfe\xff"):
        return "utf-16"
    if b"\x00" in sample[:2000]:
        return "utf-16"

    return "utf-8-sig"

def read_text_auto(path: Path) -> tuple[str, str]:
    enc = detect_encoding(path)
    try:
        return path.read_text(encoding=enc, errors="strict"), enc
    except Exception:
        for fallback in ("utf-8-sig", "utf-8", "gb18030", "big5", "latin-1"):
            try:
                return path.read_text(encoding=fallback, errors="strict"), fallback
            except Exception:
                continue

        raw = path.read_bytes()
        return raw.decode(enc, errors="replace"), enc

def detect_language(text: str, default_lang: str = "zh") -> str:
    """Defaults to Chinese ('zh') if unsure or if langdetect isn't installed."""
    sample = " ".join(text.split())[:20_000]

    letters = sum(ch.isalpha() for ch in sample)
    if len(sample) < 200 or letters < 50:
        return default_lang

    try:
        from langdetect import detect  # type: ignore
        from langdetect import DetectorFactory  # type: ignore

        DetectorFactory.seed = 0
        lang = detect(sample)
        if isinstance(lang, str) and lang:
            return lang.lower()
    except Exception:
        pass

    return default_lang


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_into_chapters(text: str) -> list[tuple[str, str]]:
    """
    Split text into chapters using common CN/EN chapter heading patterns.

    Returns list of (title_line, body_text). If no headings found, returns one chapter.

    Headings matched (start of line):
      - Chinese: 第1章 / 第十二章 / 第1回 / 第三回 / 第1节 / 第三节 (allows spaces)
      - English: Chapter 1 / CHAPTER 1

    Also keeps any leading content before the first heading as a "前言" chapter.
    """
    text = _normalize_newlines(text)
    lines = text.split("\n")

    cn_num = r"[0-9一二三四五六七八九十百千两零]+"
    cn_heading = re.compile(rf"^\s*第\s*{cn_num}\s*(章|回|节)\s*.*$")
    en_heading = re.compile(r"^\s*(?:Chapter|CHAPTER)\s+\d+\s*.*$")

    heading_idxs: list[int] = []
    for i, line in enumerate(lines):
        if cn_heading.match(line) or en_heading.match(line):
            heading_idxs.append(i)

    if not heading_idxs:
        return [("正文", text.strip())]

    chapters: list[tuple[str, str]] = []
    opening = "\n".join(lines[:heading_idxs[0]]).strip()
    if opening:
        chapters.append(("前言", opening))

    for k, start_idx in enumerate(heading_idxs):
        end_idx = heading_idxs[k + 1] if k + 1 < len(heading_idxs) else len(lines)
        title_line = lines[start_idx].strip() or f"第{k+1}章"
        body = "\n".join(lines[start_idx + 1 : end_idx]).strip()
        chapters.append((title_line, body))

    return chapters


def text_to_xhtml_body(text: str) -> str:
    """
    Plain text -> XHTML body.

    Primary mode: paragraphs split by blank lines.
    Fallback mode: if there are no blank lines, treat each non-empty line as a paragraph.
    """
    text = _normalize_newlines(text).strip()
    if not text:
        return ""

    # Split by blank lines first
    paras = re.split(r"\n\s*\n+", text)

    # Fallback: no blank lines => one-paragraph-per-line TXT
    if len(paras) == 1:
        lines = [ln.strip() for ln in text.split("\n")]
        lines = [ln for ln in lines if ln]
        return "\n".join(f"<p>{html.escape(ln)}</p>" for ln in lines)

    out: list[str] = []
    for p in paras:
        p = p.strip()
        if not p:
            continue

        # Join wrapped lines inside a paragraph
        lines = [line.strip() for line in p.split("\n")]
        joined = " ".join([ln for ln in lines if ln])
        out.append(f"<p>{html.escape(joined)}</p>")

    return "\n".join(out)



def txt_to_epub(
    input_txt: str,
    output_epub: str,
    css: str,
    title: str | None = None,
    author: str = "Unknown",
    language: str | None = None,
    log: Optional[Callable[[str], None]] = None,
) -> EpubResult:
    """
    TXT -> EPUB via ebooklib.

    Uses:
      - encoding auto-detect: detect_encoding/read_text_auto
      - language default/detect: detect_language (default zh)
      - chapter splitting + flat TOC
      - 4-digit chapter filenames
      - optional GUI logger callback

    Raises on error; GUI should catch and display.
    """
    def _log(msg: str) -> None:
        if log is not None:
            log(msg)

    in_path = Path(input_txt)
    out_path = Path(output_epub)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    _log(f"Input:  {in_path}")
    _log(f"Output: {out_path}")

    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    _log("Reading TXT (auto-detect encoding)...")
    text, enc_used = read_text_auto(in_path)

    _log("Detecting language...")
    lang = (language or detect_language(text, default_lang="zh") or "zh").lower()

    _log("Splitting chapters...")
    chapter_specs = split_into_chapters(text)
    _log(f"Detected chapters: {len(chapter_specs)}")

    css_item = epub.EpubItem(
        uid="style",
        file_name="style/main.css",
        media_type="text/css",
        content=css,
    )

    _log("Assembling EPUB...")

    book = epub.EpubBook()
    book.set_identifier(str(uuid.uuid4()))
    book.set_title(title)
    book.set_language(lang)
    book.add_author(author)

    book.add_item(epub.EpubItem(
        uid="style",
        file_name="style/main.css",
        media_type="text/css",
        content=css,
    ))

    epub_chapters: list[epub.EpubHtml] = []
    toc_items: list[epub.Link] = []

    for idx, (chap_title, chap_text) in enumerate(chapter_specs, start=1):
        file_name = f"chap{idx:04d}.xhtml"  # 4 digits

        chap = epub.EpubHtml(title=chap_title, file_name=file_name, lang=lang)
        body = text_to_xhtml_body(chap_text)

        chap.content = f"""<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="utf-8"/>
  <title>{html.escape(chap_title)}</title>
  <link rel="stylesheet" type="text/css" href="style/main.css"/>
</head>
<body>
  <h1>{html.escape(chap_title)}</h1>
  {body}
</body>
</html>"""

        chap.add_item(css_item)
        book.add_item(chap)
        epub_chapters.append(chap)
        toc_items.append(epub.Link(file_name, chap_title, f"chap{idx:04d}"))

    # Navigation metadata (keep for Kindle "Go To")
    book.toc = tuple(toc_items)
    book.add_item(epub.EpubNcx())
    #book.add_item(epub.EpubNav())
    book.spine = [*epub_chapters]

    # Optional provenance: embed in first chapter
    if epub_chapters:
        first = epub_chapters[0]
        first.content = first.content.replace(
            "</body>",
            f"<!-- source-encoding: {html.escape(enc_used)} -->\n</body>",
            1,
        )

    _log("Writing EPUB to disk...")
    # Build beside the destination, then publish with an atomic no-clobber link.
    # Unlike exists() followed by replace(), this also protects against races.
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".ebook2kindle-", suffix=".epub", dir=out_path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        if epub.write_epub(str(temporary_path), book, {"raise_exceptions": True}) is False:
            raise OSError("Could not write the EPUB file.")
        with temporary_path.open("rb") as output:
            os.fsync(output.fileno())
        requested_path = out_path
        number = 1
        while True:
            try:
                os.link(temporary_path, out_path)
                break
            except FileExistsError:
                out_path = requested_path.with_name(
                    f"{requested_path.stem} ({number}){requested_path.suffix}"
                )
                number += 1
    finally:
        temporary_path.unlink(missing_ok=True)

    return EpubResult(
        input_txt=in_path,
        output_epub=out_path,
        language=lang,
        encoding=enc_used,
    )
