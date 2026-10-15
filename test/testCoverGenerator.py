from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QColor, QImage

from cover_generator import COVER_HEIGHT, COVER_WIDTH, PALETTES, generate_cover_png


class CoverGeneratorTests(unittest.TestCase):
    def test_every_palette_has_light_background_and_dark_text(self):
        def luminance(hex_color: str) -> float:
            color = QColor(hex_color)
            channels = [color.redF(), color.greenF(), color.blueF()]
            linear = [
                channel / 12.92
                if channel <= 0.04045
                else ((channel + 0.055) / 1.055) ** 2.4
                for channel in channels
            ]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        for palette in PALETTES:
            with self.subTest(palette=palette):
                backgrounds = (
                    luminance(palette.background_top),
                    luminance(palette.background_bottom),
                )
                text = luminance(palette.text)
                self.assertGreater(min(backgrounds), 0.70)
                self.assertLess(text, 0.04)
                contrast = (min(backgrounds) + 0.05) / (text + 0.05)
                self.assertGreater(contrast, 9.0)

    def test_cover_is_deterministic_and_metadata_is_normalized(self):
        expected = generate_cover_png("The Last Light", "Avery Lin")
        normalized = generate_cover_png("  the   last light ", "avery lin")

        self.assertEqual(expected, normalized)
        self.assertTrue(expected.startswith(b"\x89PNG\r\n\x1a\n"))

        image = QImage.fromData(QByteArray(expected), "PNG")
        self.assertFalse(image.isNull())
        self.assertEqual((image.width(), image.height()), (COVER_WIDTH, COVER_HEIGHT))

    def test_long_chinese_metadata_renders_to_png(self):
        cover = generate_cover_png(
            "在漫长的冬夜里寻找一盏不会熄灭的灯",
            "林遥",
        )
        image = QImage.fromData(QByteArray(cover), "PNG")

        self.assertFalse(image.isNull())
        self.assertEqual((image.width(), image.height()), (1600, 2560))

    def test_cover_can_render_on_conversion_worker_thread(self):
        # The desktop app converts books through QThreadPool rather than the UI thread.
        generate_cover_png("Initialize Fonts", "ebook2kindle")
        with ThreadPoolExecutor(max_workers=1) as executor:
            cover = executor.submit(
                generate_cover_png,
                "线程中的封面",
                "林遥",
            ).result(timeout=10)

        self.assertTrue(cover.startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
