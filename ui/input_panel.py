"""Text input and input-mode selector."""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QPlainTextEdit, QVBoxLayout, QWidget

from core.input_detector import (
    InputDetectionError,
    detect_hanzi_only,
    detect_input,
    detect_pinyin_only,
)


class InputMode:
    AUTO = 0
    HANZI = 1
    PINYIN = 2


class InputPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("输入汉字（你好）或拼音（nǐ hǎo / ni3 hao3）…")
        self.text_edit.setMinimumHeight(100)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("自动检测", InputMode.AUTO)
        self.mode_combo.addItem("汉字模式", InputMode.HANZI)
        self.mode_combo.addItem("拼音模式", InputMode.PINYIN)

        form = QFormLayout()
        form.addRow("识别方式：", self.mode_combo)

        box = QGroupBox("输入")
        v = QVBoxLayout(box)
        v.addLayout(form)
        v.addWidget(self.text_edit)

        outer = QVBoxLayout(self)
        outer.addWidget(box)

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
