from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from gui import MainWindow
from userConfig.setting import Settings


class MainWindowShortcutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv[:1])

    def setUp(self):
        with patch("gui.load_settings", return_value=Settings()):
            self.window = MainWindow()
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_standard_close_shortcut_closes_active_window(self):
        standard_bindings = QKeySequence.keyBindings(QKeySequence.StandardKey.Close)
        self.assertTrue(standard_bindings)
        self.assertTrue(
            any(binding in self.window.close_action.shortcuts() for binding in standard_bindings)
        )

        QTest.keyClick(
            self.window,
            Qt.Key.Key_W,
            Qt.KeyboardModifier.ControlModifier,
        )
        self.app.processEvents()

        self.assertFalse(self.window.isVisible())


if __name__ == "__main__":
    unittest.main()
