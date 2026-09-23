from __future__ import annotations

import smtplib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from send2device import (
    DeliveryConfig,
    DeliveryErrorKind,
    DeliveryStatus,
    DeliveryValidationError,
    TlsMode,
    deliver_files_via_smtp,
    validate_delivery_config,
)


def delivery_config(**changes) -> DeliveryConfig:
    values = {
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_user": "sender@example.com",
        "smtp_password": "app-password",
        "to_addr": "reader@kindle.com",
        "tls_mode": TlsMode.STARTTLS,
        "max_retries": 1,
    }
    values.update(changes)
    return DeliveryConfig(**values)


def smtp_client(*, send_error=None, login_error=None):
    client = MagicMock()
    server = client.__enter__.return_value
    server.send_message.return_value = {}
    if send_error is not None:
        server.send_message.side_effect = send_error
    if login_error is not None:
        server.login.side_effect = login_error
    return client, server


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def book(self, name="book.epub") -> Path:
        path = self.directory / name
        path.write_bytes(b"valid-enough-for-delivery-tests")
        return path

    def test_starttls_submission_builds_one_message_per_book(self):
        first = self.book("first.epub")
        second = self.book("second.epub")
        first_client, first_server = smtp_client()
        second_client, second_server = smtp_client()

        with patch(
            "send2device.smtplib.SMTP",
            side_effect=[first_client, second_client],
        ) as smtp:
            results = deliver_files_via_smtp(
                delivery_config(),
                [first, second],
                sleep=lambda _delay: None,
            )

        self.assertEqual([result.status for result in results], [
            DeliveryStatus.SUBMITTED,
            DeliveryStatus.SUBMITTED,
        ])
        self.assertEqual(smtp.call_count, 2)
        first_server.starttls.assert_called_once()
        second_server.starttls.assert_called_once()
        first_server.login.assert_called_once_with("sender@example.com", "app-password")
        message = first_server.send_message.call_args.args[0]
        self.assertTrue(message["Message-ID"])
        self.assertTrue(message["Date"])
        attachments = list(message.iter_attachments())
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].get_filename(), "first.epub")
        self.assertEqual(attachments[0].get_content_type(), "application/epub+zip")

    def test_implicit_tls_uses_smtp_ssl(self):
        client, server = smtp_client()
        with (
            patch("send2device.smtplib.SMTP_SSL", return_value=client) as smtp_ssl,
            patch("send2device.smtplib.SMTP") as smtp,
        ):
            results = deliver_files_via_smtp(
                delivery_config(smtp_port=465, tls_mode=TlsMode.IMPLICIT_TLS),
                [self.book()],
            )

        self.assertTrue(results[0].succeeded)
        smtp_ssl.assert_called_once()
        smtp.assert_not_called()
        server.starttls.assert_not_called()

    def test_authentication_failure_is_typed_and_not_retried(self):
        error = smtplib.SMTPAuthenticationError(535, b"bad credentials")
        client, _server = smtp_client(login_error=error)
        with patch("send2device.smtplib.SMTP", return_value=client) as smtp:
            results = deliver_files_via_smtp(
                delivery_config(),
                [self.book()],
                sleep=lambda _delay: None,
            )

        self.assertEqual(smtp.call_count, 1)
        self.assertEqual(results[0].status, DeliveryStatus.FAILED)
        self.assertEqual(results[0].error_kind, DeliveryErrorKind.AUTHENTICATION)
        self.assertEqual(results[0].smtp_code, 535)
        self.assertNotIn("bad credentials", results[0].error_message)

    def test_transient_disconnect_is_retried_once(self):
        second_client, _second_server = smtp_client()
        with patch(
            "send2device.smtplib.SMTP",
            side_effect=[OSError("temporarily offline"), second_client],
        ) as smtp:
            results = deliver_files_via_smtp(
                delivery_config(),
                [self.book()],
                sleep=lambda _delay: None,
            )

        self.assertEqual(smtp.call_count, 2)
        self.assertTrue(results[0].succeeded)
        self.assertEqual(results[0].attempts, 2)

    def test_disconnect_during_submission_is_not_retried(self):
        client, _server = smtp_client(
            send_error=smtplib.SMTPServerDisconnected("status unknown")
        )
        with patch("send2device.smtplib.SMTP", return_value=client) as smtp:
            results = deliver_files_via_smtp(
                delivery_config(),
                [self.book()],
                sleep=lambda _delay: None,
            )

        self.assertEqual(smtp.call_count, 1)
        self.assertFalse(results[0].succeeded)
        self.assertIn("avoid a duplicate", results[0].error_message)

    def test_batch_preserves_per_book_failure(self):
        first_client, _first_server = smtp_client()
        rejection = smtplib.SMTPRecipientsRefused(
            {"reader@kindle.com": (550, b"recipient refused")}
        )
        second_client, _second_server = smtp_client(send_error=rejection)
        with patch(
            "send2device.smtplib.SMTP",
            side_effect=[first_client, second_client],
        ):
            results = deliver_files_via_smtp(
                delivery_config(),
                [self.book("accepted.epub"), self.book("rejected.epub")],
                sleep=lambda _delay: None,
            )

        self.assertTrue(results[0].succeeded)
        self.assertFalse(results[1].succeeded)
        self.assertEqual(results[1].error_kind, DeliveryErrorKind.RECIPIENT)

    def test_cleanup_error_after_acceptance_does_not_retry_or_report_failure(self):
        for error in (
            smtplib.SMTPResponseException(451, b"QUIT failed"),
            smtplib.SMTPResponseException(550, b"QUIT failed"),
            smtplib.SMTPServerDisconnected("connection closed"),
            TimeoutError("QUIT timed out"),
        ):
            with self.subTest(error=error):
                client, server = smtp_client()
                client.__exit__.side_effect = error
                with patch("send2device.smtplib.SMTP", return_value=client) as smtp:
                    results = deliver_files_via_smtp(
                        delivery_config(), [self.book()], sleep=lambda _: None,
                    )
                self.assertTrue(results[0].succeeded)
                self.assertEqual(results[0].attempts, 1)
                smtp.assert_called_once()
                server.send_message.assert_called_once()

    def test_explicit_temporary_submission_rejection_is_still_retried(self):
        rejected, _server = smtp_client(send_error=smtplib.SMTPDataError(451, b"try later"))
        accepted, _server = smtp_client()
        with patch("send2device.smtplib.SMTP", side_effect=[rejected, accepted]) as smtp:
            results = deliver_files_via_smtp(
                delivery_config(), [self.book()], sleep=lambda _: None,
            )
        self.assertTrue(results[0].succeeded)
        self.assertEqual(results[0].attempts, 2)
        self.assertEqual(smtp.call_count, 2)

    def test_invalid_config_and_attachments_fail_before_network(self):
        with self.assertRaises(DeliveryValidationError):
            validate_delivery_config(delivery_config(to_addr="not-an-email"))

        text_file = self.directory / "book.txt"
        text_file.write_text("text", encoding="utf-8")
        with (
            patch("send2device.smtplib.SMTP") as smtp,
            self.assertRaises(DeliveryValidationError),
        ):
            deliver_files_via_smtp(delivery_config(), [text_file])
        smtp.assert_not_called()


if __name__ == "__main__":
    unittest.main()
