from __future__ import annotations


APP_STYLESHEET = """
QWidget {
    color: #1E2026;
    font-family: "Inter", "SF Pro Text", "Helvetica Neue", sans-serif;
    font-size: 13px;
}
QMainWindow, QWidget#appRoot, QDialog {
    background: #F6F6F9;
}
QLabel#brandMark {
    color: white;
    background: #6D5DFC;
    border-radius: 11px;
    font-size: 19px;
    font-weight: 700;
}
QLabel#muted, QLabel#caption {
    color: #707582;
}
QLabel#caption {
    font-size: 11px;
}
QLabel#kicker {
    color: #6D5DFC;
    font-size: 11px;
    font-weight: 700;
}
QLabel#hero {
    font-size: 28px;
    font-weight: 700;
}
QLabel#sectionTitle {
    font-size: 15px;
    font-weight: 700;
}
QLabel#cardTitle {
    font-size: 14px;
    font-weight: 700;
}
QLabel#fileName, QLabel#value {
    font-weight: 600;
}
QFrame#sidebar, QFrame#queueShell, QFrame#settingsCard {
    background: #FFFFFF;
    border: 1px solid #E0E1E8;
    border-radius: 18px;
}
QFrame#destinationCard {
    background: #F1F1F6;
    border: none;
    border-radius: 13px;
}
QFrame#dropZone {
    background: #FAF9FF;
    border: 2px dashed #B8B2F8;
    border-radius: 18px;
}
QFrame#queueRow {
    background: #FFFFFF;
    border-bottom: 1px solid #ECECF1;
}
QFrame#queueRow:last-child {
    border-bottom: none;
}
QLabel#fileMark {
    color: #6D5DFC;
    background: #EFEDFF;
    border-radius: 9px;
    font-size: 10px;
    font-weight: 700;
}
QLabel#statusReady {
    color: #707582;
    background: #F1F1F6;
    border-radius: 9px;
    padding: 4px 9px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#statusWorking {
    color: #956300;
    background: #FFF4D6;
    border-radius: 9px;
    padding: 4px 9px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#statusSuccess {
    color: #237A57;
    background: #E8F5EE;
    border-radius: 9px;
    padding: 4px 9px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#statusError {
    color: #B42318;
    background: #FDECEA;
    border-radius: 9px;
    padding: 4px 9px;
    font-size: 11px;
    font-weight: 600;
}
QPushButton {
    min-height: 38px;
    padding: 0 15px;
    color: #30333A;
    background: #FFFFFF;
    border: 1px solid #D9DAE2;
    border-radius: 10px;
    font-weight: 600;
}
QPushButton:hover {
    background: #F3F3F7;
    border-color: #CBCDD7;
}
QPushButton:pressed {
    background: #EBEBF1;
}
QPushButton:disabled {
    color: #A5A7AF;
    background: #EEEEF2;
    border-color: #E5E5EA;
}
QPushButton#primaryButton {
    color: #FFFFFF;
    background: #6D5DFC;
    border-color: #6D5DFC;
    font-weight: 700;
}
QPushButton#primaryButton:hover {
    background: #5D4DED;
    border-color: #5D4DED;
}
QPushButton#compactButton {
    min-height: 30px;
    padding: 0 11px;
    border-radius: 9px;
    font-size: 11px;
}
QPushButton#removeButton {
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
    color: #7A7F8A;
    background: transparent;
    border: none;
    border-radius: 8px;
    font-size: 18px;
    font-weight: 400;
}
QPushButton#removeButton:hover {
    color: #B42318;
    background: #FDECEA;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    min-height: 38px;
    padding: 0 11px;
    background: #FFFFFF;
    border: 1px solid #D9DAE2;
    border-radius: 10px;
    selection-background-color: #6D5DFC;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 2px solid #6D5DFC;
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #CACBD3;
    border-radius: 6px;
    background: #FFFFFF;
}
QCheckBox::indicator:checked {
    background: #6D5DFC;
    border-color: #6D5DFC;
    image: none;
}
QProgressBar {
    min-height: 8px;
    max-height: 8px;
    background: #EEEFF3;
    border: none;
    border-radius: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background: #6D5DFC;
    border-radius: 4px;
}
QScrollArea {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    width: 10px;
    background: transparent;
    margin: 6px 2px;
}
QScrollBar::handle:vertical {
    min-height: 26px;
    background: #CFD0D8;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QFrame#segmentedControl {
    background: #EDEDF3;
    border: none;
    border-radius: 13px;
}
QPushButton#segmentedButton {
    min-height: 36px;
    padding: 0 16px;
    color: #707582;
    background: transparent;
    border: none;
    border-radius: 9px;
    font-weight: 600;
}
QPushButton#segmentedButton:hover {
    color: #343740;
    background: #E4E4EC;
}
QPushButton#segmentedButton:checked {
    color: #5549E8;
    background: #FFFFFF;
}
QPushButton#securityOption {
    min-height: 42px;
    padding: 0 10px;
}
QPushButton#securityOption:checked {
    color: #5549E8;
    background: #EFEDFF;
    border: 2px solid #6D5DFC;
}
QPushButton#securityOption:focus {
    border: 2px solid #6D5DFC;
}
QFrame#frontStyleSetting {
    background: #F8F8FB;
    border: 1px solid #E0E1E8;
    border-radius: 13px;
}
QLabel#smallValuePill {
    min-width: 52px;
    padding: 4px 7px;
    color: #5549E8;
    background: #EFEDFF;
    border-radius: 8px;
    font-size: 11px;
    font-weight: 700;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #E6E6EC;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #6D5DFC;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 18px;
    height: 18px;
    margin: -6px 0;
    background: #FFFFFF;
    border: 2px solid #6D5DFC;
    border-radius: 9px;
}
QSlider::handle:horizontal:hover {
    background: #F3F1FF;
}
QLabel#errorLabel {
    color: #B42318;
}
"""
