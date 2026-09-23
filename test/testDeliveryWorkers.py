from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gui import ConversionWorker, SendWorker
from send2device import DeliveryConfig, DeliveryResult, DeliveryStatus
from userConfig.css_config import generate_css


class DeliveryWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.book = Path(self.temporary_directory.name) / "book.epub"
        self.book.write_bytes(b"epub-placeholder")
        self.config = DeliveryConfig(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="sender@example.com",
            smtp_password="app-password",
            to_addr="reader@kindle.com",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    @staticmethod
    def successful_delivery(_config, files, *, on_result=None, **_kwargs):
        results = []
        for file in files:
            result = DeliveryResult(
                file=Path(file).resolve(),
                status=DeliveryStatus.SUBMITTED,
                attempts=1,
                message_id="<test@example.com>",
            )
            results.append(result)
            if on_result:
                on_result(result)
        return results

    def test_conversion_worker_emits_structured_delivery_results(self):
        worker = ConversionWorker(
            [str(self.book)],
            generate_css(),
            self.config,
        )
        statuses = []
        finished = []
        worker.signals.file_status.connect(lambda path, status: statuses.append((path, status)))
        worker.signals.finished.connect(lambda *values: finished.append(values))

        with patch("gui.deliver_files_via_smtp", side_effect=self.successful_delivery):
            worker.run()

        self.assertIn((str(self.book), "Submitted"), statuses)
        self.assertEqual(len(finished), 1)
        self.assertTrue(finished[0][3][0].succeeded)
        self.assertIsNone(finished[0][4])

    def test_send_worker_reports_each_output(self):
        worker = SendWorker(self.config, [str(self.book)])
        statuses = []
        finished = []
        worker.signals.file_status.connect(lambda path, status: statuses.append((path, status)))
        worker.signals.finished.connect(lambda *values: finished.append(values))

        with patch("gui.deliver_files_via_smtp", side_effect=self.successful_delivery):
            worker.run()

        self.assertEqual(statuses, [(str(self.book.resolve()), "Submitted")])
        self.assertTrue(finished[0][0][0].succeeded)
        self.assertIsNone(finished[0][1])


if __name__ == "__main__":
    unittest.main()
