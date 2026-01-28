from __future__ import annotations

import zipfile
import tempfile
from pathlib import Path

# Change this import to match your file name/module
# e.g. if your functions are in txt2epub.py, use:
# from txt2epub import txt_to_epub
from txt2epub import txt_to_epub


def assert_epub_structure(epub_path: Path) -> None:
    assert epub_path.exists(), f"EPUB not found: {epub_path}"
    assert zipfile.is_zipfile(epub_path), f"Not a valid zip/epub: {epub_path}"

    with zipfile.ZipFile(epub_path, "r") as z:
        names = set(z.namelist())

    required = {
        "mimetype",
        "META-INF/container.xml",
    }
    missing = required - names
    if missing:
        raise AssertionError(f"Missing required EPUB entries: {sorted(missing)}")

    # ebooklib typically puts content under EPUB/ by default in some setups,
    # but your code uses style/main.css and chap*.xhtml, so check broadly.
    has_any_xhtml = any(n.endswith(".xhtml") for n in names)
    has_ncx = any(n.endswith(".ncx") for n in names)
    has_nav = any(n.endswith("nav.xhtml") or "nav" in n.lower() for n in names)

    if not has_any_xhtml:
        raise AssertionError("No .xhtml content found in EPUB.")
    if not has_ncx:
        raise AssertionError("No .ncx found (TOC).")
    if not has_nav:
        # Some ebooklib versions name nav differently; keep this as a warning, not fail
        print("[WARN] Could not confidently find nav document; may still be OK depending on ebooklib version.")


def main():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        inp = tmp / "sample.txt"
        out = tmp / "sample.epub"

        # Sample text includes characters that must be escaped in XHTML
        # and includes chapter-like headings (if your function supports splitting).
        sample = """这是一本测试书 & <测试>。

第1章 起始
第一段内容。
第二行仍然属于同一段。

这是另一个段落。

第2章 发展
这里是第二章内容。
包含一些英文 Chapter 3 should not trigger unless you support English headings.

Chapter 3 A New Start
If you support English headings, this should be a chapter too.
"""

        inp.write_text(sample, encoding="utf-8")

        print(f"[TEST] Input:  {inp}")
        print(f"[TEST] Output: {out}")

        result = txt_to_epub(
            input_txt=str(inp),
            output_epub=str(out),
            title="测试书",
            author="Tianyu Lu",
            # language=None  # let your function detect/default
        )

        epub_path = Path(result)
        print(f"[OK] txt_to_epub returned: {epub_path}")

        assert_epub_structure(epub_path)
        print("[OK] Basic EPUB structure looks good.")

        # Optional: inspect how many chapters were produced
        with zipfile.ZipFile(epub_path, "r") as z:
            xhtml_files = sorted([n for n in z.namelist() if n.endswith(".xhtml")])
        print(f"[INFO] XHTML files inside EPUB ({len(xhtml_files)}):")
        for n in xhtml_files:
            print(f"  - {n}")

        print("\nAll tests passed.")


if __name__ == "__main__":
    main()
