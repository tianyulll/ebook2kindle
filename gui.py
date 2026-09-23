from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, Slot
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from send2device import (
    DeliveryConfig,
    DeliveryResult,
    TlsMode,
    deliver_files_via_smtp,
    validate_delivery_config,
)
from ui_theme import APP_STYLESHEET
from userConfig import SettingsDialog, generate_css, load_settings, save_settings
from util import convert_format


SUPPORTED_EXTENSIONS = {".txt", ".epub"}


def _human_size(path: str) -> str:
    try:
        size = Path(path).stat().st_size
    except OSError:
        return "Unknown size"

    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit in {"B", "KB"} else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit in {"B", "KB"} else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _masked_email(address: str) -> str:
    address = (address or "").strip()
    if "@" not in address:
        return address
    local, domain = address.rsplit("@", 1)
    visible = local[:2] if len(local) > 2 else local[:1]
    return f"{visible}•••@{domain}"


def _label(text: str, object_name: str | None = None, word_wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    if object_name:
        widget.setObjectName(object_name)
    widget.setWordWrap(word_wrap)
    return widget


def _delivery_config(settings) -> DeliveryConfig:
    password = settings.get_sender_password()
    return validate_delivery_config(
        DeliveryConfig(
            smtp_host=settings.smtp_host.strip(),
            smtp_port=int(settings.smtp_port or 587),
            smtp_user=settings.sender_email.strip(),
            smtp_password=password,
            to_addr=settings.kindle_email.strip(),
            tls_mode=TlsMode(settings.smtp_tls_mode),
            timeout_seconds=settings.smtp_timeout_seconds,
            max_retries=settings.smtp_max_retries,
        )
    )


class ConversionSignals(QObject):
    file_status = Signal(str, str)
    activity = Signal(str)
    progress = Signal(int)
    finished = Signal(object, object, bool, object, object)


class ConversionWorker(QRunnable):
    def __init__(
        self,
        files: list[str],
        css: str,
        delivery_config: DeliveryConfig | None,
    ):
        super().__init__()
        self.files = files
        self.css = css
        self.delivery_config = delivery_config
        self.send_after = delivery_config is not None
        self.signals = ConversionSignals()

    @Slot()
    def run(self):
        completed: list[tuple[str, str]] = []
        failures: list[tuple[str, str]] = []
        total = len(self.files)

        for index, path in enumerate(self.files, start=1):
            self.signals.file_status.emit(path, "Converting…")
            self.signals.activity.emit(f"Converting {index} of {total}: {Path(path).name}")
            try:
                output = convert_format(path, self.css)
                completed.append((path, output))
                self.signals.file_status.emit(path, "Converted")
            except Exception as exc:
                failures.append((path, str(exc)))
                self.signals.file_status.emit(path, "Failed")

            maximum = 80 if self.send_after else 100
            self.signals.progress.emit(int((index / max(total, 1)) * maximum))

        delivery_error = None
        delivery_results: list[DeliveryResult] = []
        if self.send_after and completed:
            for source, _output in completed:
                self.signals.file_status.emit(source, "Submitting…")
            self.signals.activity.emit("Submitting converted books to the mail provider…")
            try:
                output_to_source = {str(Path(output).resolve()): source for source, output in completed}

                def report_result(result: DeliveryResult):
                    source = output_to_source.get(str(result.file.resolve()))
                    if source:
                        self.signals.file_status.emit(
                            source,
                            "Submitted" if result.succeeded else "Delivery failed",
                        )

                delivery_results = deliver_files_via_smtp(
                    self.delivery_config,
                    [output for _source, output in completed],
                    on_result=report_result,
                )
            except Exception as exc:
                delivery_error = str(exc)
                for source, _output in completed:
                    self.signals.file_status.emit(source, "Converted")

        self.signals.finished.emit(
            completed,
            failures,
            self.send_after,
            delivery_results,
            delivery_error,
        )


class SendSignals(QObject):
    file_status = Signal(str, str)
    progress = Signal(int)
    finished = Signal(object, object)


class SendWorker(QRunnable):
    def __init__(self, config: DeliveryConfig, files: list[str]):
        super().__init__()
        self.config = config
        self.files = files
        self.signals = SendSignals()

    @Slot()
    def run(self):
        error = None
        results: list[DeliveryResult] = []
        try:
            total = len(self.files)

            def report_result(result: DeliveryResult):
                self.signals.file_status.emit(
                    str(result.file),
                    "Submitted" if result.succeeded else "Delivery failed",
                )
                self.signals.progress.emit(
                    85 + round((len(results) + 1) / max(total, 1) * 15)
                )
                results.append(result)

            deliver_files_via_smtp(
                self.config,
                self.files,
                on_result=report_result,
            )
        except Exception as exc:
            error = str(exc)
        self.signals.finished.emit(results, error)


class DropZone(QFrame):
    files_dropped = Signal(list)

    def __init__(self, choose_callback, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(178)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(7)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = _label("⇧", "brandMark")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(46, 46)
        title = _label("Drop TXT or EPUB files here", "cardTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copy = _label("Batch conversion supported · Files remain on this computer", "caption")
        copy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        choose = QPushButton("Choose files")
        choose.clicked.connect(choose_callback)
        choose.setFixedWidth(132)

        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(copy)
        layout.addWidget(choose, alignment=Qt.AlignmentFlag.AlignCenter)
        self.choose_button = choose

    def dragEnterEvent(self, event: QDragEnterEvent):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if any(Path(path).suffix.lower() in SUPPORTED_EXTENSIONS for path in paths):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        self.files_dropped.emit(paths)
        event.acceptProposedAction()


class FileRow(QFrame):
    remove_requested = Signal(str)

    def __init__(self, path: str, status: str, busy: bool, parent=None):
        super().__init__(parent)
        self.path = path
        self.setObjectName("queueRow")
        self.setMinimumHeight(70)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(13, 10, 10, 10)
        layout.setSpacing(11)

        suffix = Path(path).suffix.upper().lstrip(".") or "FILE"
        mark = _label(suffix, "fileMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(46, 46)
        layout.addWidget(mark)

        copy = QVBoxLayout()
        copy.setSpacing(3)
        name = _label(Path(path).name, "fileName")
        name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        detail = _label(f"{suffix} · {_human_size(path)}", "caption")
        copy.addWidget(name)
        copy.addWidget(detail)
        layout.addLayout(copy, 1)

        badge_name = "statusReady"
        if status in {"Converting…", "Sending…", "Submitting…"}:
            badge_name = "statusWorking"
        elif status in {"Converted", "Submitted"}:
            badge_name = "statusSuccess"
        elif status in {"Failed", "Delivery failed"}:
            badge_name = "statusError"
        badge = _label(status, badge_name)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(badge)

        remove = QPushButton("×")
        remove.setObjectName("removeButton")
        remove.setToolTip(f"Remove {Path(path).name}")
        remove.setEnabled(not busy)
        remove.clicked.connect(lambda: self.remove_requested.emit(self.path))
        layout.addWidget(remove)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ebook2kindle")
        self.resize(1040, 740)
        self.setMinimumSize(900, 660)

        self.settings = load_settings()
        self.selected_files: list[str] = []
        self.output_files: list[str] = []
        self.output_by_source: dict[str, str] = {}
        self.file_status: dict[str, str] = {}
        self.is_busy = False
        self.current_worker = None
        self.thread_pool = QThreadPool.globalInstance()

        self._build_ui()
        self._refresh_settings_summary()
        self._refresh_queue()
        self._update_action_states()

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("appRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 24)
        content_layout.setSpacing(24)
        content_layout.addWidget(self._build_workspace(), 1)
        content_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(content, 1)

    def _build_workspace(self) -> QWidget:
        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(_label("CONVERT & DELIVER", "kicker"))
        hero = _label("Turn text files into Kindle books", "hero")
        layout.addWidget(hero)
        layout.addSpacing(18)

        self.drop_zone = DropZone(self._choose_files)
        self.drop_zone.files_dropped.connect(self._add_files)
        layout.addWidget(self.drop_zone)
        layout.addSpacing(20)

        queue_heading = QHBoxLayout()
        queue_heading.addWidget(_label("Conversion queue", "sectionTitle"))
        queue_heading.addStretch(1)
        self.queue_count_label = _label("No files", "muted")
        queue_heading.addWidget(self.queue_count_label)
        layout.addLayout(queue_heading)
        layout.addSpacing(9)

        self.queue_shell = QFrame()
        self.queue_shell.setObjectName("queueShell")
        self.queue_shell.setMinimumHeight(190)
        self.queue_shell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        queue_shell_layout = QVBoxLayout(self.queue_shell)
        queue_shell_layout.setContentsMargins(1, 1, 1, 1)
        queue_shell_layout.setSpacing(0)

        self.queue_scroll = QScrollArea()
        self.queue_scroll.setWidgetResizable(True)
        self.queue_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.queue_content = QWidget()
        self.queue_content.setStyleSheet("background: transparent;")
        self.queue_layout = QVBoxLayout(self.queue_content)
        self.queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_layout.setSpacing(0)
        self.queue_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.queue_scroll.setWidget(self.queue_content)
        queue_shell_layout.addWidget(self.queue_scroll)
        layout.addWidget(self.queue_shell, 1)
        layout.addSpacing(14)

        actions = QHBoxLayout()
        actions.setSpacing(9)
        actions.addWidget(_label("EPUBs are saved beside their source files.", "muted"), 1)
        self.clear_button = QPushButton("Clear")
        self.clear_button.setFixedWidth(76)
        self.clear_button.clicked.connect(self._reset)
        self.send_button = QPushButton("Send to Kindle")
        self.send_button.setFixedWidth(122)
        self.send_button.clicked.connect(self._send)
        self.process_button = QPushButton("Convert books")
        self.process_button.setFixedWidth(122)
        self.process_button.setObjectName("primaryButton")
        self.process_button.clicked.connect(self._convert)
        actions.addWidget(self.clear_button)
        actions.addWidget(self.send_button)
        actions.addWidget(self.process_button)
        layout.addLayout(actions)

        return workspace

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(310)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(19, 19, 19, 19)
        layout.setSpacing(9)

        delivery_heading = QHBoxLayout()
        delivery_heading.addWidget(_label("Kindle delivery", "cardTitle"))
        delivery_heading.addStretch(1)
        self.settings_button = QPushButton("Settings")
        self.settings_button.setObjectName("compactButton")
        self.settings_button.setToolTip("Configure Kindle delivery and SMTP")
        self.settings_button.clicked.connect(self._open_settings)
        delivery_heading.addWidget(self.settings_button)
        layout.addLayout(delivery_heading)
        layout.addWidget(
            _label(
                "Send converted books automatically when the queue finishes.",
                "muted",
                True,
            )
        )

        destination = QFrame()
        destination.setObjectName("destinationCard")
        destination_layout = QVBoxLayout(destination)
        destination_layout.setContentsMargins(13, 11, 13, 11)
        destination_layout.setSpacing(3)
        destination_layout.addWidget(_label("SEND TO", "caption"))
        self.destination_label = _label("Not configured", "value")
        destination_layout.addWidget(self.destination_label)
        layout.addWidget(destination)

        self.send_after_check = QCheckBox("Send after conversion")
        self.send_after_check.toggled.connect(self._update_action_states)
        layout.addWidget(self.send_after_check)
        self.delivery_note = _label("", "caption", True)
        layout.addWidget(self.delivery_note)
        layout.addSpacing(12)
        layout.addWidget(_label("Book styling", "cardTitle"))
        layout.addWidget(
            _label(
                "Applied to every TXT file in the queue.",
                "muted",
                True,
            )
        )

        indent_card, self.indent_slider, self.indent_value_label = self._build_style_control(
            "Paragraph indent",
            "Distance from the left edge",
            round(self.settings.text_indent_em * 10),
            60,
        )
        spacing_card, self.spacing_slider, self.spacing_value_label = self._build_style_control(
            "Paragraph spacing",
            "Space between paragraphs",
            round(self.settings.paragraph_spacing_em * 10),
            30,
        )
        self.indent_slider.valueChanged.connect(self._save_styling)
        self.spacing_slider.valueChanged.connect(self._save_styling)
        layout.addWidget(indent_card)
        layout.addWidget(spacing_card)

        layout.addSpacing(12)
        layout.addWidget(_label("Activity", "cardTitle"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        self.activity_label = _label("Add files to begin.", "caption", True)
        layout.addWidget(self.activity_label)
        layout.addStretch(1)
        return sidebar

    def _build_style_control(
        self,
        title: str,
        caption: str,
        value: int,
        maximum: int,
    ) -> tuple[QFrame, QSlider, QLabel]:
        card = QFrame()
        card.setObjectName("frontStyleSetting")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 12)
        card_layout.setSpacing(6)

        heading = QHBoxLayout()
        heading.addWidget(_label(title, "value"))
        heading.addStretch(1)
        value_label = _label(f"{value / 10:.1f} em", "smallValuePill")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.addWidget(value_label)
        card_layout.addLayout(heading)
        card_layout.addWidget(_label(caption, "caption"))

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, maximum)
        slider.setSingleStep(1)
        slider.setValue(value)
        card_layout.addWidget(slider)
        return card, slider, value_label

    # ------------------------------------------------------------------
    # Queue
    # ------------------------------------------------------------------
    def _choose_files(self):
        if self.is_busy:
            return
        paths, _selected_filter = QFileDialog.getOpenFileNames(
            self,
            "Choose books",
            "",
            "Supported books (*.txt *.epub);;Text files (*.txt);;EPUB files (*.epub);;All files (*)",
        )
        self._add_files(paths)

    def _add_files(self, paths):
        if self.is_busy:
            return
        existing = set(self.selected_files)
        skipped: list[str] = []
        added = 0
        for raw_path in paths:
            path = str(Path(raw_path).expanduser().resolve())
            if Path(path).suffix.lower() not in SUPPORTED_EXTENSIONS:
                skipped.append(Path(path).name)
                continue
            if path in existing:
                continue
            self.selected_files.append(path)
            self.file_status[path] = "Ready"
            existing.add(path)
            added += 1

        if added:
            self.activity_label.setText(f"{added} file{'s' if added != 1 else ''} added and ready.")
            self.progress_bar.setValue(0)
        if skipped:
            self.activity_label.setText("Only TXT and EPUB files are supported.")

        self._refresh_queue()
        self._update_action_states()

    def _remove_file(self, path: str):
        if self.is_busy:
            return
        if path in self.selected_files:
            self.selected_files.remove(path)
        self.file_status.pop(path, None)
        output = self.output_by_source.pop(path, None)
        if output in self.output_files:
            self.output_files.remove(output)
        self._refresh_queue()
        self._update_action_states()

    def _clear_queue_widgets(self):
        while self.queue_layout.count():
            item = self.queue_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _refresh_queue(self):
        self._clear_queue_widgets()
        if not self.selected_files:
            empty = QWidget()
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(20, 30, 20, 30)
            empty_layout.setSpacing(5)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title = _label("Your conversion queue is empty", "value")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            copy = _label("Drop files above or choose them from Finder.", "caption")
            copy.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(title)
            empty_layout.addWidget(copy)
            self.queue_layout.addWidget(empty)
            self.queue_count_label.setText("No files")
            return

        total_bytes = 0
        for path in self.selected_files:
            try:
                total_bytes += Path(path).stat().st_size
            except OSError:
                pass
            row = FileRow(path, self.file_status.get(path, "Ready"), self.is_busy)
            row.remove_requested.connect(self._remove_file)
            self.queue_layout.addWidget(row)

        self.queue_layout.addStretch(1)
        count = len(self.selected_files)
        self.queue_count_label.setText(
            f"{count} file{'s' if count != 1 else ''} · {_format_bytes(total_bytes)}"
        )

    # ------------------------------------------------------------------
    # Conversion and delivery
    # ------------------------------------------------------------------
    def _convert(self):
        if self.is_busy or not self.selected_files:
            return
        self.settings = load_settings()
        send_after = self.send_after_check.isChecked()
        delivery_config = None
        if send_after:
            try:
                delivery_config = _delivery_config(self.settings)
            except Exception as exc:
                self.activity_label.setText(f"Delivery settings need attention: {exc}")
                self._open_settings()
                return

        css = generate_css(
            text_indent_em=self.settings.text_indent_em,
            paragraph_spacing_em=self.settings.paragraph_spacing_em,
        )
        files = list(self.selected_files)
        self.output_files.clear()
        self.output_by_source.clear()
        for path in files:
            self.file_status[path] = "Ready"

        self._set_busy(True)
        self.activity_label.setText("Preparing conversion…")
        self.progress_bar.setValue(0)

        worker = ConversionWorker(files, css, delivery_config)
        worker.signals.file_status.connect(self._set_file_status)
        worker.signals.activity.connect(self.activity_label.setText)
        worker.signals.progress.connect(self.progress_bar.setValue)
        worker.signals.finished.connect(self._finish_conversion)
        self.current_worker = worker
        self.thread_pool.start(worker)

    def _finish_conversion(
        self,
        completed,
        failures,
        send_after: bool,
        delivery_results,
        delivery_error,
    ):
        self.current_worker = None
        self.output_by_source = dict(completed)
        self.output_files = [output for _source, output in completed]
        self.progress_bar.setValue(100 if completed or failures else 0)
        self._set_busy(False)

        submitted = sum(result.succeeded for result in delivery_results)
        delivery_failures = len(delivery_results) - submitted

        if delivery_error:
            self.activity_label.setText(f"Conversion finished, but delivery failed: {delivery_error}")
        elif send_after and delivery_failures:
            self.activity_label.setText(
                f"Submitted {submitted} book{'s' if submitted != 1 else ''}; "
                f"{delivery_failures} failed delivery."
            )
        elif send_after and failures:
            self.activity_label.setText(
                f"Submitted {submitted} book{'s' if submitted != 1 else ''}; "
                f"{len(failures)} failed conversion."
            )
        elif send_after and submitted:
            self.activity_label.setText(
                f"Converted and submitted {submitted} book{'s' if submitted != 1 else ''}."
            )
        elif failures and completed:
            self.activity_label.setText(
                f"Converted {len(completed)} file{'s' if len(completed) != 1 else ''}; "
                f"{len(failures)} failed."
            )
        elif failures:
            self.activity_label.setText("Conversion failed. Check the source file and try again.")
        elif send_after and not completed:
            self.activity_label.setText("Nothing was converted or submitted.")
        else:
            self.activity_label.setText(
                f"Converted {len(completed)} book{'s' if len(completed) != 1 else ''}."
            )
        self._refresh_queue()
        self._update_action_states()

    def _send(self):
        if self.is_busy or not self.output_files:
            return
        self.settings = load_settings()
        try:
            delivery_config = _delivery_config(self.settings)
        except Exception as exc:
            self.activity_label.setText(f"Delivery settings need attention: {exc}")
            self._open_settings()
            return

        for source, output in self.output_by_source.items():
            if output in self.output_files:
                self.file_status[source] = "Submitting…"
        self._set_busy(True)
        self.activity_label.setText("Submitting converted books to the mail provider…")
        self.progress_bar.setValue(85)

        worker = SendWorker(delivery_config, list(self.output_files))
        worker.signals.file_status.connect(self._set_output_status)
        worker.signals.progress.connect(self.progress_bar.setValue)
        worker.signals.finished.connect(self._finish_send)
        self.current_worker = worker
        self.thread_pool.start(worker)

    def _finish_send(self, results, error):
        self.current_worker = None
        if error:
            for source, output in self.output_by_source.items():
                if output in self.output_files and self.file_status.get(source) == "Submitting…":
                    self.file_status[source] = "Converted"
        self.progress_bar.setValue(100)
        self._set_busy(False)
        if error:
            self.activity_label.setText(f"Kindle delivery failed: {error}")
        else:
            submitted = sum(result.succeeded for result in results)
            failed = len(results) - submitted
            if failed:
                self.activity_label.setText(
                    f"Submitted {submitted} book{'s' if submitted != 1 else ''}; "
                    f"{failed} failed delivery."
                )
            else:
                self.activity_label.setText(
                    f"Submitted {submitted} book{'s' if submitted != 1 else ''} to Kindle."
                )
        self._refresh_queue()

    def _set_output_status(self, output_path: str, status: str):
        resolved_output = str(Path(output_path).resolve())
        for source, output in self.output_by_source.items():
            if str(Path(output).resolve()) == resolved_output:
                self.file_status[source] = status
                break
        self._refresh_queue()

    def _set_file_status(self, path: str, status: str):
        self.file_status[path] = status
        self._refresh_queue()

    def _set_busy(self, busy: bool):
        self.is_busy = busy
        self._refresh_queue()
        self._update_action_states()

    # ------------------------------------------------------------------
    # Settings and controls
    # ------------------------------------------------------------------
    def _open_settings(self):
        if self.is_busy:
            return

        def on_saved(updated_settings):
            self.settings = updated_settings
            self._refresh_settings_summary()
            self.activity_label.setText("Settings saved.")
            self._update_action_states()

        dialog = SettingsDialog(self, settings=load_settings(), on_saved=on_saved)
        dialog.exec()

    def _refresh_settings_summary(self):
        self.settings = load_settings()
        destination = self.settings.kindle_email.strip()
        self.destination_label.setText(_masked_email(destination) if destination else "Not configured")
        self.delivery_note.setText(
            "Delivery is configured and ready."
            if self._mail_is_configured()
            else "Add a Kindle address and sender credentials to enable delivery."
        )
        for slider, value in (
            (self.indent_slider, round(self.settings.text_indent_em * 10)),
            (self.spacing_slider, round(self.settings.paragraph_spacing_em * 10)),
        ):
            slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(False)
        self.indent_value_label.setText(f"{self.settings.text_indent_em:.1f} em")
        self.spacing_value_label.setText(f"{self.settings.paragraph_spacing_em:.1f} em")

    def _save_styling(self, _value=None):
        self.settings.text_indent_em = self.indent_slider.value() / 10
        self.settings.paragraph_spacing_em = self.spacing_slider.value() / 10
        self.indent_value_label.setText(f"{self.settings.text_indent_em:.1f} em")
        self.spacing_value_label.setText(f"{self.settings.paragraph_spacing_em:.1f} em")
        try:
            save_settings(self.settings)
        except Exception as exc:
            self.activity_label.setText(f"Could not save book styling: {exc}")

    def _mail_is_configured(self) -> bool:
        return all(
            (
                self.settings.kindle_email.strip(),
                self.settings.sender_email.strip(),
                self.settings.has_sender_password(),
                self.settings.smtp_host.strip(),
                self.settings.smtp_tls_mode in {"starttls", "implicit_tls"},
            )
        )

    def _update_action_states(self):
        self.process_button.setText("Convert books")
        self.process_button.setToolTip(
            "Convert the queue and send successful books to Kindle."
            if self.send_after_check.isChecked()
            else "Convert the queue to EPUB."
        )
        self.process_button.setEnabled(bool(self.selected_files) and not self.is_busy)
        self.clear_button.setEnabled(bool(self.selected_files) and not self.is_busy)
        self.send_button.setEnabled(bool(self.output_files) and not self.is_busy)
        self.settings_button.setEnabled(not self.is_busy)
        self.indent_slider.setEnabled(not self.is_busy)
        self.spacing_slider.setEnabled(not self.is_busy)
        self.drop_zone.choose_button.setEnabled(not self.is_busy)
        self.send_after_check.setEnabled(not self.is_busy)
        self.drop_zone.setAcceptDrops(not self.is_busy)

    def _reset(self):
        if self.is_busy:
            return
        self.selected_files.clear()
        self.output_files.clear()
        self.output_by_source.clear()
        self.file_status.clear()
        self.progress_bar.setValue(0)
        self.activity_label.setText("Add files to begin.")
        self._refresh_queue()
        self._update_action_states()


class App:
    def __init__(self):
        self.qt_app = QApplication.instance() or QApplication(sys.argv)
        self.qt_app.setApplicationName("ebook2kindle")
        self.qt_app.setOrganizationName("ebook2kindle")
        self.qt_app.setStyleSheet(APP_STYLESHEET)
        self.window = MainWindow()

    def run(self) -> int:
        self.window.show()
        return self.qt_app.exec()
