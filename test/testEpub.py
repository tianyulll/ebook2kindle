from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from txt2epub import split_into_chapters, txt_to_epub
from util import convert_format
from userConfig.css_config import generate_css


def assert_epub_structure(epub_path: Path) -> None:
    if not epub_path.exists():
        raise AssertionError(f"EPUB not found: {epub_path}")
    if not zipfile.is_zipfile(epub_path):
        raise AssertionError(f"Not a valid zip/epub: {epub_path}")

    with zipfile.ZipFile(epub_path, "r") as archive:
        names = set(archive.namelist())

    required = {"mimetype", "META-INF/container.xml"}
    missing = required - names
    if missing:
        raise AssertionError(f"Missing required EPUB entries: {sorted(missing)}")
    if not any(name.endswith(".xhtml") for name in names):
        raise AssertionError("No XHTML content found in EPUB.")
    if not any(name.endswith(".ncx") for name in names):
        raise AssertionError("No NCX table of contents found in EPUB.")


class EpubConversionTests(unittest.TestCase):
    def test_opening_content_is_preserved(self):
        for heading in ("Chapter 1 Beginning", "第1章 起始"):
            with self.subTest(heading=heading):
                chapters = split_into_chapters(f"Preface & introduction.\n\n{heading}\nBody.")
                self.assertEqual(chapters, [
                    ("前言", "Preface & introduction."), (heading, "Body."),
                ])
                self.assertEqual(
                    split_into_chapters(f"\n\n{heading}\nBody."), [(heading, "Body.")],
                )

    def test_existing_outputs_are_preserved_and_actual_path_returned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "book.txt"
            source.write_text("Chapter 1 Beginning\nBody.", encoding="utf-8")
            for name in ("book.epub", "book (1).epub"):
                (root / name).write_bytes(b"original book")
            output = Path(convert_format(str(source), generate_css()))
            self.assertEqual(output, (root / "book (2).epub").resolve())
            assert_epub_structure(output)
            for name in ("book.epub", "book (1).epub"):
                self.assertEqual((root / name).read_bytes(), b"original book")
            self.assertFalse(list(root.glob(".ebook2kindle-*")))

    def test_failed_write_does_not_publish_or_damage_output(self):
        for existing in (False, True):
            for raises in (False, True):
                with self.subTest(existing=existing, raises=raises), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    source = root / "book.txt"
                    source.write_text("Chapter 1 Beginning\nBody.", encoding="utf-8")
                    output = root / "book.epub"
                    if existing:
                        output.write_bytes(b"original book")

                    def failed_write(path, *_args):
                        Path(path).write_bytes(b"partial archive")
                        if raises:
                            raise OSError("disk full")
                        return False

                    with patch("txt2epub.epub.write_epub", side_effect=failed_write):
                        with self.assertRaises(OSError):
                            convert_format(str(source), generate_css())
                    if existing:
                        self.assertEqual(output.read_bytes(), b"original book")
                    else:
                        self.assertFalse(output.exists())
                    self.assertFalse((root / "book (1).epub").exists())
                    self.assertFalse(list(root.glob(".ebook2kindle-*")))

    def test_output_created_during_conversion_is_not_overwritten(self):
        from ebooklib import epub
        real_write = epub.write_epub
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "book.txt"
            source.write_text("Chapter 1 Beginning\nBody.", encoding="utf-8")
            output = root / "book.epub"

            def concurrent_write(*args, **kwargs):
                result = real_write(*args, **kwargs)
                output.write_bytes(b"another process's book")
                return result

            with patch("txt2epub.epub.write_epub", side_effect=concurrent_write):
                actual = Path(convert_format(str(source), generate_css()))
            self.assertEqual(output.read_bytes(), b"another process's book")
            self.assertEqual(actual, (root / "book (1).epub").resolve())
            assert_epub_structure(actual)

    def test_basic_epub_structure(self):
        with tempfile.TemporaryDirectory() as directory:
            temp_dir = Path(directory)
            source = temp_dir / "sample.txt"
            output = temp_dir / "sample.epub"
            source.write_text(
                """这是一本测试书 & <测试>。

第1章 起始
第一段内容。

第2章 发展
这里是第二章内容。

Chapter 3 A New Start
English chapter content.
""",
                encoding="utf-8",
            )

            result = txt_to_epub(
                input_txt=source,
                output_epub=output,
                css=generate_css(),
                title="测试书",
                author="Tianyu Lu",
            )

            epub_path = Path(result.output_epub)
            assert_epub_structure(epub_path)
            with zipfile.ZipFile(epub_path, "r") as archive:
                xhtml_files = [
                    name for name in archive.namelist() if name.endswith(".xhtml")
                ]
                content = "\n".join(archive.read(name).decode("utf-8") for name in xhtml_files)
            self.assertIn("这是一本测试书 &amp; &lt;测试&gt;。", content)
            self.assertGreaterEqual(len(xhtml_files), 4)


if __name__ == "__main__":
    unittest.main()
