from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .setting import Settings, save_settings


def _label(text: str, object_name: str | None = None, word_wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    if object_name:
        widget.setObjectName(object_name)
    widget.setWordWrap(word_wrap)
    return widget


class SettingsDialog(QDialog):
    def __init__(self, parent, settings: Settings, on_saved=None):
        super().__init__(parent)
        self.settings = settings
        self.on_saved = on_saved

        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(700, 570)
        self.setMinimumSize(640, 540)

        self._create_widgets()

    def _create_widgets(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 16, 24, 16)
        outer.setSpacing(10)

        title = _label("Settings", "hero")
        subtitle = _label(
            "Configure Kindle delivery and advanced mail settings.",
            "muted",
            True,
        )
        outer.addWidget(title)
        outer.addWidget(subtitle)

        navigation = QFrame()
        navigation.setObjectName("segmentedControl")
        navigation_layout = QHBoxLayout(navigation)
        navigation_layout.setContentsMargins(4, 4, 4, 4)
        navigation_layout.setSpacing(4)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._create_delivery_tab())
        self.pages.addWidget(self._create_advanced_tab())

        self.section_buttons: list[QPushButton] = []
        for index, title_text in enumerate(("Kindle delivery", "Advanced SMTP")):
            button = QPushButton(title_text)
            button.setObjectName("segmentedButton")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.toggled.connect(
                lambda checked, page=index: self.pages.setCurrentIndex(page) if checked else None
            )
            navigation_layout.addWidget(button, 1)
            self.section_buttons.append(button)
        self.section_buttons[0].setChecked(True)

        outer.addWidget(navigation)
        outer.addWidget(self.pages, 1)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        self.error_label = _label("", "errorLabel", True)
        footer.addWidget(self.error_label, 1)

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save settings")
        save.setObjectName("primaryButton")
        save.clicked.connect(self._save)
        footer.addWidget(cancel)
        footer.addWidget(save)
        outer.addLayout(footer)

    def _tab_card(self) -> tuple[QWidget, QVBoxLayout]:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(22, 12, 22, 12)
        layout.setSpacing(8)
        return tab, layout

    def _create_delivery_tab(self) -> QWidget:
        tab, layout = self._tab_card()
        layout.setSpacing(6)
        layout.addWidget(_label("Kindle destination", "cardTitle"))
        layout.addWidget(
            _label(
                "Use the Kindle address listed in your Amazon device settings.",
                "muted",
                True,
            )
        )

        self.kindle_email_input = QLineEdit(self.settings.kindle_email)
        self.kindle_email_input.setPlaceholderText("reader@kindle.com")
        layout.addWidget(self._field_group("Kindle email", self.kindle_email_input))

        self.sender_email_input = QLineEdit(self.settings.sender_email)
        self.sender_email_input.setPlaceholderText("you@example.com")
        layout.addWidget(self._field_group("Sender email", self.sender_email_input))

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(
            "Leave blank to keep the saved password"
            if self.settings.has_sender_password()
            else "Enter an app-specific password"
        )
        layout.addWidget(self._field_group("App password", self.password_input))

        show_password = QCheckBox("Show password")
        show_password.toggled.connect(
            lambda checked: self.password_input.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        layout.addWidget(show_password)

        hint = (
            "A password is already saved. Leave the field blank to keep it."
            if self.settings.has_sender_password()
            else "Use an app-specific password rather than your account password."
        )
        layout.addWidget(_label(hint, "caption", True))
        layout.addStretch(1)
        return tab

    @staticmethod
    def _field_group(title: str, field: QWidget) -> QWidget:
        group = QWidget()
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(4)
        group_layout.addWidget(_label(title, "value"))
        group_layout.addWidget(field)
        return group

    def _create_advanced_tab(self) -> QWidget:
        tab, layout = self._tab_card()
        layout.addWidget(_label("SMTP connection", "cardTitle"))
        layout.addWidget(
            _label(
                "The Gmail defaults work for most users. Change these only if your provider requires it.",
                "muted",
                True,
            )
        )

        layout.addWidget(_label("SMTP host", "value"))
        self.smtp_host_input = QLineEdit(self.settings.smtp_host)
        layout.addWidget(self.smtp_host_input)

        layout.addWidget(_label("SMTP port", "value"))
        self.smtp_port_input = QSpinBox()
        self.smtp_port_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.smtp_port_input.setRange(1, 65535)
        self.smtp_port_input.setValue(int(self.settings.smtp_port))
        self.smtp_port_input.setFixedWidth(130)
        layout.addWidget(self.smtp_port_input, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(_label("Connection security", "value"))
        security_options = QWidget()
        options_layout = QHBoxLayout(security_options)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(10)
        self.tls_mode_group = QButtonGroup(self)
        for index, (title, mode) in enumerate((
            ("STARTTLS (recommended)", "starttls"),
            ("Implicit TLS", "implicit_tls"),
        )):
            button = QPushButton(title)
            button.setObjectName("securityOption")
            button.setCheckable(True)
            button.setAutoDefault(False)
            button.setProperty("tlsMode", mode)
            self.tls_mode_group.addButton(button, index)
            options_layout.addWidget(button, 1)
        selected = 1 if self.settings.smtp_tls_mode == "implicit_tls" else 0
        self.tls_mode_group.button(selected).setChecked(True)
        self.tls_mode_group.idClicked.connect(self._sync_tls_port)
        layout.addWidget(security_options)
        layout.addStretch(1)
        return tab

    def _sync_tls_port(self):
        if self.smtp_port_input.value() not in {465, 587}:
            return
        self.smtp_port_input.setValue(
            465 if self.tls_mode_group.checkedId() == 1 else 587
        )

    def _show_error(self, message: str, widget=None):
        self.error_label.setText(message)
        if widget is not None:
            widget.setFocus(Qt.FocusReason.OtherFocusReason)

    def _save(self):
        self.error_label.clear()
        kindle_email = self.kindle_email_input.text().strip()
        sender_email = self.sender_email_input.text().strip()
        sender_password = self.password_input.text().strip()
        smtp_host = self.smtp_host_input.text().strip() or "smtp.gmail.com"

        self.settings.kindle_email = kindle_email
        self.settings.sender_email = sender_email
        self.settings.smtp_host = smtp_host
        self.settings.smtp_port = int(self.smtp_port_input.value())
        self.settings.smtp_tls_mode = str(self.tls_mode_group.checkedButton().property("tlsMode"))

        if sender_password:
            try:
                self.settings.set_sender_password(sender_password)
            except Exception as exc:
                self._show_error(
                    f"Could not store the password securely: {exc}",
                    self.password_input,
                )
                return

        try:
            save_settings(self.settings)
        except Exception as exc:
            self._show_error(f"Could not save settings: {exc}")
            return

        if callable(self.on_saved):
            self.on_saved(self.settings)
        self.accept()
