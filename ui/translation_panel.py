"""Translation tab: EN<->ZH with pinyin preview and send-to-trainer."""

from __future__ import annotations

import re

from pypinyin import Style, lazy_pinyin
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.translator import TranslationError, translate_text

_CJK_RE = re.compile(r"[\u3400-\u9fff]")


def _contains_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text))


def _pinyin_preview(text: str) -> str:
    if not _contains_cjk(text):
        return ""
    tokens = lazy_pinyin(
        text,
        style=Style.TONE,
        neutral_tone_with_five=True,
        tone_sandhi=True,
        errors=lambda x: list(x),
    )
    return " ".join(t for t in tokens if t.strip())


class TranslationPanel(QWidget):
    """Translate text and optionally send Chinese output to trainer."""

    send_to_trainer = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._result_chinese: str = ""

        self._group = QGroupBox("Translation")
        lay = QVBoxLayout(self._group)

        self._input = QPlainTextEdit()
        self._input.setPlaceholderText("Type English or Chinese")
        self._input.setMinimumHeight(110)

        self._direction = QComboBox()
        self._direction.addItem("English -> Chinese", ("en", "zh-CN"))
        self._direction.addItem("Chinese -> English", ("zh-CN", "en"))
        self._direction.addItem("Auto-detect", ("auto", "auto"))

        self._btn_translate = QPushButton("Translate")
        self._btn_send = QPushButton("▶ Send to Trainer")
        self._btn_send.setEnabled(False)

        row = QHBoxLayout()
        row.addWidget(self._btn_translate)
        row.addWidget(self._btn_send)

        form = QFormLayout()
        form.addRow("Direction:", self._direction)

        self._result_label = QLabel("Translation:")
        self._result = QPlainTextEdit()
        self._result.setReadOnly(True)
        self._result.setMinimumHeight(80)

        self._pinyin_label = QLabel("Pinyin:")
        self._pinyin = QPlainTextEdit()
        self._pinyin.setReadOnly(True)
        self._pinyin.setMinimumHeight(60)

        lay.addLayout(form)
        lay.addWidget(self._input)
        lay.addLayout(row)
        lay.addWidget(self._result_label)
        lay.addWidget(self._result)
        lay.addWidget(self._pinyin_label)
        lay.addWidget(self._pinyin)

        outer = QVBoxLayout(self)
        outer.addWidget(self._group)

        self._btn_translate.clicked.connect(self._on_translate)
        self._btn_send.clicked.connect(self._on_send)

    def _resolve_direction(self, text: str) -> tuple[str, str]:
        data = self._direction.currentData()
        if not isinstance(data, tuple) or len(data) != 2:
            return "auto", "zh-CN"
        src, dst = str(data[0]), str(data[1])
        if src == "auto" and dst == "auto":
            if _contains_cjk(text):
                return "zh-CN", "en"
            return "en", "zh-CN"
        return src, dst

    def _on_translate(self) -> None:
        self._btn_send.setEnabled(False)
        self._result_chinese = ""
        self._result.clear()
        self._pinyin.clear()

        text = self._input.toPlainText().strip()
        if not text:
            self._result.setPlainText("Please enter text.")
            return
        src, dst = self._resolve_direction(text)
        try:
            translated = translate_text(text, source=src, target=dst)
        except TranslationError as e:
            if e.key == "empty_input":
                self._result.setPlainText("Please enter text.")
            else:
                self._result.setPlainText(f"Translation failed: {e.detail or e.key}")
            return

        if dst.lower().startswith("zh"):
            chinese_text = translated
            self._result.setPlainText(chinese_text)
            self._result_chinese = chinese_text
            self._pinyin.setPlainText(_pinyin_preview(chinese_text))
            self._btn_send.setEnabled(bool(chinese_text.strip()))
        else:
            self._result.setPlainText(translated)
            source_chinese = text if src.lower().startswith("zh") and _contains_cjk(text) else ""
            self._result_chinese = source_chinese.strip()
            self._pinyin.setPlainText(_pinyin_preview(self._result_chinese))
            self._btn_send.setEnabled(bool(self._result_chinese))

    def _on_send(self) -> None:
        chinese = self._result_chinese.strip()
        if chinese:
            self.send_to_trainer.emit(chinese)
