"""Text input and input-mode selector."""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from core.input_detector import (
    InputDetectionError,
    detect_hanzi_only,
    detect_input,
    detect_pinyin_only,
)
from ui.i18n import UiTexts


class InputMode:
    AUTO = 0
    HANZI = 1
    PINYIN = 2


class InputPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setMinimumHeight(100)

        self.mode_combo = QComboBox()
        self._lbl_mode = QLabel()

        form = QFormLayout()
        form.addRow(self._lbl_mode, self.mode_combo)

        self._group = QGroupBox()
        v = QVBoxLayout(self._group)
        v.addLayout(form)
        v.addWidget(self.text_edit)

        outer = QVBoxLayout(self)
        outer.addWidget(self._group)

    def apply_language(self, t: UiTexts) -> None:
        self._group.setTitle(t.group_input)
        self._lbl_mode.setText(t.label_detection_mode)
        cur = self.mode_combo.currentData()
        self.mode_combo.clear()
        self.mode_combo.addItem(t.mode_auto, InputMode.AUTO)
        self.mode_combo.addItem(t.mode_hanzi, InputMode.HANZI)
        self.mode_combo.addItem(t.mode_pinyin, InputMode.PINYIN)
        if cur is not None:
            idx = self.mode_combo.findData(cur)
            self.mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.text_edit.setPlaceholderText(t.placeholder_input)

    def plain_text(self) -> str:
        return self.text_edit.toPlainText()

    def detect(self):
        """Return ``InputDetection`` or raise ``InputDetectionError``."""
        text = self.plain_text()
        mode = self.mode_combo.currentData()
        if mode == InputMode.AUTO:
            return detect_input(text)
        if mode == InputMode.HANZI:
            return detect_hanzi_only(text)
        return detect_pinyin_only(text)
