"""Deterministic, offline book-cover rendering for generated EPUB files."""

from __future__ import annotations

import hashlib
import random
import sys
import unicodedata
from dataclasses import dataclass

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QApplication


COVER_WIDTH = 1600
COVER_HEIGHT = 2560
_cover_application: QApplication | None = None


@dataclass(frozen=True)
class Palette:
    background_top: str
    background_bottom: str
    accent: str
    text: str
    quiet: str


PALETTES = (
    Palette("#f4f0e7", "#ebe4d8", "#bd5b46", "#17222b", "#b9b1a5"),
    Palette("#edf1f4", "#e1e7ec", "#315f7d", "#14232d", "#a8b4bd"),
    Palette("#e7ece7", "#dce4de", "#376958", "#172722", "#a5b2aa"),
    Palette("#eee9e5", "#e4dcd6", "#765a86", "#271f2c", "#b8acb8"),
)


def _ensure_application() -> QApplication:
    global _cover_application
    instance = QApplication.instance()
    if instance is not None:
        if not isinstance(instance, QApplication):
            raise RuntimeError("Cover rendering requires a QApplication instance.")
        return instance
    _cover_application = QApplication([sys.argv[0], "--cover-renderer"])
    return _cover_application


def normalize_metadata(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").split()).strip()


def metadata_seed(title: str, author: str) -> int:
    normalized_title = normalize_metadata(title).casefold()
    normalized_author = normalize_metadata(author).casefold()
    digest = hashlib.sha256(f"{normalized_title}\0{normalized_author}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def contains_cjk(value: str) -> bool:
    return any(
        "\u3400" <= character <= "\u9fff"
        or "\uf900" <= character <= "\ufaff"
        for character in value
    )


def _wrapped_lines(text: str, metrics: QFontMetricsF, max_width: float) -> list[str]:
    lines: list[str] = []
    current = ""
    for character in text:
        candidate = current + character
        if current and metrics.horizontalAdvance(candidate) > max_width:
            if " " in current:
                line, remainder = current.rsplit(" ", 1)
                lines.append(line.strip())
                current = (remainder + character).lstrip()
            else:
                lines.append(current.strip())
                current = character.lstrip()
        else:
            current = candidate
    if current.strip():
        lines.append(current.strip())
    return lines


def _fit_title(
    title: str,
    max_width: float,
    max_height: float = 900,
    max_lines: int = 5,
) -> tuple[QFont, list[str], bool]:
    display_title = normalize_metadata(title).upper() or "UNTITLED"
    cjk = contains_cjk(display_title)
    family = "Songti SC" if cjk else "Baskerville"
    line_factor = 0.98 if cjk else 0.88
    for size in range(238, 55, -4):
        font = QFont(family, size, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3 if cjk else 2)
        metrics = QFontMetricsF(font)
        lines = _wrapped_lines(display_title, metrics, max_width)
        title_height = metrics.height() * line_factor * len(lines)
        if (
            len(lines) <= max_lines
            and title_height <= max_height
            and max(metrics.horizontalAdvance(line) for line in lines) <= max_width
        ):
            return font, lines, cjk
    return font, lines, cjk


def _fit_author(author: str, max_width: float) -> tuple[QFont, str]:
    display_author = normalize_metadata(author).upper() or "UNKNOWN AUTHOR"
    cjk = contains_cjk(display_author)
    family = "PingFang SC" if cjk else "Avenir Next"
    for size in range(76, 39, -2):
        font = QFont(family, size, QFont.Weight.DemiBold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 7 if cjk else 18)
        if QFontMetricsF(font).horizontalAdvance(display_author) <= max_width:
            return font, display_author
    return font, display_author


def render_cover(title: str, author: str) -> QImage:
    """Render the cover into a new QImage using only local vector drawing."""
    _ensure_application()
    title = normalize_metadata(title) or "Untitled"
    author = normalize_metadata(author) or "Unknown Author"
    seed = metadata_seed(title, author)
    rng = random.Random(seed)
    palette = PALETTES[seed % len(PALETTES)]

    image = QImage(
        COVER_WIDTH,
        COVER_HEIGHT,
        QImage.Format.Format_ARGB32_Premultiplied,
    )
    image.fill(QColor(palette.background_top))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    backdrop = QLinearGradient(0, 0, 0, COVER_HEIGHT)
    backdrop.setColorAt(0, QColor(palette.background_top))
    backdrop.setColorAt(1, QColor(palette.background_bottom))
    painter.fillRect(image.rect(), backdrop)

    painter.setPen(Qt.PenStyle.NoPen)
    grain = QColor(palette.quiet)
    for _ in range(950):
        grain.setAlpha(rng.randint(5, 16))
        painter.setBrush(grain)
        radius = rng.uniform(0.5, 1.6)
        painter.drawEllipse(
            QPointF(rng.uniform(0, COVER_WIDTH), rng.uniform(0, COVER_HEIGHT)),
            radius,
            radius,
        )

    motif_size = rng.randint(560, 700)
    motif_x = (COVER_WIDTH - motif_size) / 2 + rng.randint(-110, 110)
    motif_y = rng.randint(1230, 1390)
    accent = QColor(palette.accent)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(accent, 18, Qt.PenStyle.SolidLine))
    painter.drawEllipse(QRectF(motif_x, motif_y, motif_size, motif_size))

    quiet = QColor(palette.quiet)
    quiet.setAlpha(175)
    painter.setPen(QPen(quiet, 4, Qt.PenStyle.SolidLine))
    rule_y = motif_y + motif_size / 2 + rng.randint(-80, 80)
    painter.drawLine(QPointF(175, rule_y), QPointF(COVER_WIDTH - 175, rule_y))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(accent)
    square_size = rng.randint(44, 72)
    painter.drawRect(QRectF(COVER_WIDTH - 210, 150, square_size, square_size))

    title_font, title_lines, title_is_cjk = _fit_title(title, COVER_WIDTH - 260)
    painter.setFont(title_font)
    painter.setPen(QColor(palette.text))
    metrics = QFontMetricsF(title_font)
    line_height = metrics.height() * (0.98 if title_is_cjk else 0.88)
    title_height = line_height * len(title_lines)
    title_y = max(180.0, 710.0 - title_height / 2)
    for index, line in enumerate(title_lines):
        rect = QRectF(
            100,
            title_y + index * line_height,
            COVER_WIDTH - 200,
            line_height * 1.15,
        )
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, line)

    author_font, display_author = _fit_author(author, COVER_WIDTH - 300)
    painter.setFont(author_font)
    painter.drawText(
        QRectF(100, 2250, COVER_WIDTH - 200, 160),
        Qt.AlignmentFlag.AlignCenter,
        display_author,
    )
    painter.end()
    return image


def generate_cover_png(title: str, author: str) -> bytes:
    """Return a standards-compatible PNG cover as bytes."""
    image = render_cover(title, author)
    data = QByteArray()
    buffer = QBuffer(data)
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError("Could not open the in-memory cover buffer.")
    try:
        if not image.save(buffer, "PNG"):
            raise OSError("Could not encode the generated cover as PNG.")
    finally:
        buffer.close()
    return bytes(data)
