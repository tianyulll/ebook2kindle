from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from userConfig.setting import Settings, encrypt_text, save_settings


class SettingsTests(unittest.TestCase):
    def test_new_password_is_stored_in_os_credential_store(self):
        settings = Settings(sender_pass_enc="legacy-token")
        with patch("userConfig.setting.keyring.set_password") as set_password:
            settings.set_sender_password("new-app-password")

        set_password.assert_called_once_with(
            "ebook2kindle.smtp",
            "default",
            "new-app-password",
        )
        self.assertTrue(settings.sender_password_saved)
        self.assertEqual(settings.sender_pass_enc, "")

    def test_legacy_password_migrates_to_credential_store(self):
        with tempfile.TemporaryDirectory() as directory:
            temp_dir = Path(directory)
            key_path = temp_dir / "secret.key"
            settings_path = temp_dir / "settings.json"
            with (
                patch("userConfig.setting.get_key_path", return_value=key_path),
                patch("userConfig.setting.get_settings_path", return_value=settings_path),
            ):
                settings = Settings(sender_pass_enc=encrypt_text("legacy-password"))
                with (
                    patch("userConfig.setting.keyring.get_password", return_value=None),
                    patch("userConfig.setting.keyring.set_password") as set_password,
                ):
                    password = settings.get_sender_password()

            self.assertEqual(password, "legacy-password")
            set_password.assert_called_once_with(
                "ebook2kindle.smtp",
                "default",
                "legacy-password",
            )
            self.assertEqual(settings.sender_pass_enc, "")
            self.assertTrue(settings.sender_password_saved)
            saved = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["sender_pass_enc"], "")
            self.assertTrue(saved["sender_password_saved"])

    def test_legacy_tls_setting_migrates_without_plaintext_mode(self):
        implicit = Settings.from_dict({"smtp_port": 465, "smtp_use_tls": False})
        fallback = Settings.from_dict({"smtp_port": 587, "smtp_use_tls": False})

        self.assertEqual(implicit.smtp_tls_mode, "implicit_tls")
        self.assertEqual(fallback.smtp_tls_mode, "starttls")

    def test_settings_write_is_atomic_and_versioned(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / "settings.json"
            with patch("userConfig.setting.get_settings_path", return_value=settings_path):
                save_settings(Settings())

            payload = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 2)
            self.assertFalse(list(Path(directory).glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
