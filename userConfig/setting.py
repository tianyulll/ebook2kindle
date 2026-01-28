from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json

APP_DIR_NAME = "ebook2kindle"  # change if needed


def get_settings_path() -> Path:
    base = Path.home() / f".{APP_DIR_NAME}"
    base.mkdir(parents=True, exist_ok=True)
    return base / "settings.json"


@dataclass
class Settings:
    # --- CSS knobs ---
    text_indent_em: float = 1.0
    paragraph_spacing_em: float = 0.3

    # --- Email settings (for "Send to Kindle") ---
    kindle_email: str = ""       # e.g. name_123@kindle.com
    sender_email: str = ""       # e.g. your_gmail@gmail.com
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_use_tls: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Settings":
        s = Settings()
        if not isinstance(d, dict):
            return s

        def _get_float(key: str, default: float) -> float:
            try:
                return float(d.get(key, default))
            except Exception:
                return default

        def _get_int(key: str, default: int) -> int:
            try:
                return int(d.get(key, default))
            except Exception:
                return default

        def _get_bool(key: str, default: bool) -> bool:
            v = d.get(key, default)
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                return v.strip().lower() in {"1", "true", "yes", "y", "on"}
            if isinstance(v, int):
                return v != 0
            return default

        def _get_str(key: str, default: str = "") -> str:
            v = d.get(key, default)
            return v if isinstance(v, str) else default

        # CSS knobs
        s.text_indent_em = _get_float("text_indent_em", s.text_indent_em)
        s.paragraph_spacing_em = _get_float("paragraph_spacing_em", s.paragraph_spacing_em)

        # Email settings
        s.kindle_email = _get_str("kindle_email", s.kindle_email).strip()
        s.sender_email = _get_str("sender_email", s.sender_email).strip()
        s.smtp_host = _get_str("smtp_host", s.smtp_host).strip() or s.smtp_host
        s.smtp_port = _get_int("smtp_port", s.smtp_port)
        s.smtp_use_tls = _get_bool("smtp_use_tls", s.smtp_use_tls)

        return s


def load_settings() -> Settings:
    path = get_settings_path()
    if not path.exists():
        return Settings()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Settings.from_dict(data)
    except Exception:
        return Settings()


def save_settings(settings: Settings) -> None:
    path = get_settings_path()
    path.write_text(
        json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
