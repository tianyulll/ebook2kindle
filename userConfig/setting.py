from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import os
import tempfile

from cryptography.fernet import Fernet, InvalidToken
import keyring
from keyring.errors import KeyringError

APP_DIR_NAME = "ebook2kindle" 
KEYRING_SERVICE = "ebook2kindle.smtp"
KEYRING_ACCOUNT = "default"


# ----------------------------
# Paths
# ----------------------------
def get_app_dir() -> Path:
    base = Path.home() / f".{APP_DIR_NAME}"
    base.mkdir(parents=True, exist_ok=True)
    try:
        if os.name != "nt":
            os.chmod(base, 0o700)
    except OSError:
        pass
    return base


def get_settings_path() -> Path:
    return get_app_dir() / "settings.json"


def get_key_path() -> Path:
    return get_app_dir() / "secret.key"


# ----------------------------
# Local crypto helpers
# ----------------------------
class CryptoError(RuntimeError):
    pass


def get_or_create_key() -> bytes:
    kp = get_key_path()
    if kp.exists():
        try:
            if os.name != "nt":
                os.chmod(kp, 0o600)
        except OSError:
            pass
        key = kp.read_bytes()
        # Fernet keys are urlsafe-base64 bytes; basic sanity check
        if len(key) < 40:
            raise CryptoError("Corrupted key file (too short).")
        return key

    key = Fernet.generate_key()
    kp.write_bytes(key)

    # Best-effort permission hardening on POSIX
    try:
        if os.name != "nt":
            os.chmod(kp, 0o600)
    except Exception:
        pass

    return key


def encrypt_text(plain: str) -> str:
    if plain is None:
        raise CryptoError("Nothing to encrypt.")
    f = Fernet(get_or_create_key())
    token = f.encrypt(plain.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(token: str) -> str:
    if not token:
        raise CryptoError("Empty encrypted token.")
    f = Fernet(get_or_create_key())
    try:
        plain = f.decrypt(token.encode("utf-8"))
    except InvalidToken as e:
        raise CryptoError("Failed to decrypt (wrong key or corrupted token).") from e
    return plain.decode("utf-8")


# ----------------------------
# Settings model
# ----------------------------
@dataclass
class Settings:
    schema_version: int = 2

    # --- CSS knobs ---
    text_indent_em: float = 1.0
    paragraph_spacing_em: float = 0.3

    # --- Email settings (for "Send to Kindle") ---
    kindle_email: str = ""       # e.g. name_123@kindle.com
    sender_email: str = ""       # e.g. your_gmail@gmail.com
    sender_pass_enc: str = ""    # legacy encrypted password; cleared after Keychain migration
    sender_password_saved: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_tls_mode: str = "starttls"
    smtp_timeout_seconds: float = 30.0
    smtp_max_retries: int = 1

    # ----- convenience API for UI / sender code -----
    def set_sender_password(self, plain_password: str) -> None:
        """
        Store the sender password in the operating-system credential store.
        """
        plain_password = (plain_password or "").strip()
        if not plain_password:
            return
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_ACCOUNT, plain_password)
        except KeyringError as exc:
            raise CryptoError("The operating-system credential store is unavailable.") from exc
        self.sender_password_saved = True
        self.sender_pass_enc = ""

    def has_sender_password(self) -> bool:
        return bool(self.sender_password_saved or self.sender_pass_enc)

    def get_sender_password(self) -> str:
        """
        Decrypts and returns plaintext password for SMTP login.
        """
        try:
            password = keyring.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
        except KeyringError as exc:
            raise CryptoError("The operating-system credential store is unavailable.") from exc
        if password:
            self.sender_password_saved = True
            return password
        if not self.sender_pass_enc:
            return ""

        password = decrypt_text(self.sender_pass_enc)
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_ACCOUNT, password)
        except KeyringError as exc:
            raise CryptoError("Could not migrate the saved password to the credential store.") from exc
        self.sender_pass_enc = ""
        self.sender_password_saved = True
        try:
            save_settings(self)
            get_key_path().unlink(missing_ok=True)
        except OSError:
            pass
        return password

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
        s.sender_pass_enc = _get_str("sender_pass_enc", s.sender_pass_enc).strip()
        s.sender_password_saved = _get_bool(
            "sender_password_saved",
            s.sender_password_saved,
        )
        s.smtp_host = _get_str("smtp_host", s.smtp_host).strip() or s.smtp_host
        s.smtp_port = _get_int("smtp_port", s.smtp_port)
        tls_mode = _get_str("smtp_tls_mode", "").strip().lower()
        if tls_mode not in {"starttls", "implicit_tls"}:
            legacy_starttls = _get_bool("smtp_use_tls", True)
            tls_mode = "implicit_tls" if not legacy_starttls and s.smtp_port == 465 else "starttls"
        s.smtp_tls_mode = tls_mode
        s.smtp_timeout_seconds = _get_float(
            "smtp_timeout_seconds",
            s.smtp_timeout_seconds,
        )
        s.smtp_max_retries = _get_int("smtp_max_retries", s.smtp_max_retries)
        s.schema_version = 2

        return s


# ----------------------------
# Load / save
# ----------------------------
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
    payload = json.dumps(settings.to_dict(), ensure_ascii=False, indent=2)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="settings-",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(payload)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary_path.unlink(missing_ok=True)
        raise
