"""Text input and input-mode selector."""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.input_detector import (
    InputDetectionError,
    detect_hanzi_only,
    detect_input,
    detect_pinyin_only,
)
from ui.i18n import UiTexts

HISTORY_MAX = 10


class InputMode:
    AUTO = 0
    HANZI = 1
    PINYIN = 2


class InputPanel(QWidget):
    def __init__(self, history_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._history_path = history_path
        self._loading_history = False

        self.text_edit = QPlainTextEdit()
        self.text_edit.setMinimumHeight(100)

        self.mode_combo = QComboBox()
        self._lbl_mode = QLabel()

        self._lbl_history = QLabel()
        self.history_combo = QComboBox()
        self.history_combo.setMinimumContentsLength(24)

        form = QFormLayout()
        form.addRow(self._lbl_mode, self.mode_combo)

        form_hist = QFormLayout()
        form_hist.addRow(self._lbl_history, self.history_combo)

        self._group = QGroupBox()
        v = QVBoxLayout(self._group)
        v.addLayout(form)
        v.addLayout(form_hist)
        v.addWidget(self.text_edit)

        outer = QVBoxLayout(self)
        outer.addWidget(self._group)

        self.history_combo.activated.connect(self._on_history_activated)
        self._load_history_into_combo()

    def _read_history_file(self) -> list[str]:
        if not self._history_path.is_file():
            return []
        try:
            raw = json.loads(self._history_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(raw, list):
            return []
        out: list[str] = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
        return out

    def _write_history_file(self, items: list[str]) -> None:
        try:
            self._history_path.parent.mkdir(parents=True, exist_ok=True)
            self._history_path.write_text(
                json.dumps(items, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    def _load_history_into_combo(self) -> None:
        self._loading_history = True
        self.history_combo.blockSignals(True)
        self.history_combo.clear()
        for s in self._read_history_file():
            self.history_combo.addItem(s, s)
        self.history_combo.blockSignals(False)
        self._loading_history = False

    def _on_history_activated(self, index: int) -> None:
        if self._loading_history or index < 0:
            return
        data = self.history_combo.itemData(index)
        if isinstance(data, str) and data:
            self.text_edit.setPlainText(data)

    def record_successful_play(self, text: str) -> None:
        """Remember last played input (unique, max 10), and refresh the dropdown."""
        t = text.strip()
        if not t:
            return
        cur = self._read_history_file()
        cur = [x for x in cur if x != t]
        cur.insert(0, t)
        cur = cur[:HISTORY_MAX]
        self._write_history_file(cur)
        self._load_history_into_combo()

    def apply_language(self, t: UiTexts) -> None:
        self._group.setTitle(t.group_input)
        self._lbl_mode.setText(t.label_detection_mode)
        self._lbl_history.setText(t.label_history)
        cur = self.mode_combo.currentData()
        self.mode_combo.clear()
        self.mode_combo.addItem(t.mode_auto, InputMode.AUTO)
        self.mode_combo.addItem(t.mode_hanzi, InputMode.HANZI)
        self.mode_combo.addItem(t.mode_pinyin, InputMode.PINYIN)
        if cur is not None:
            idx = self.mode_combo.findData(cur)
            self.mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.text_edit.setPlaceholderText(t.placeholder_input)
        self.history_combo.setPlaceholderText(t.history_placeholder)

    def plain_text(self) -> str:
        return self.text_edit.toPlainText()

    def set_plain_text(self, text: str) -> None:
        self.text_edit.setPlainText(text)

    def detect(self):
        """Return ``InputDetection`` or raise ``InputDetectionError``."""
        text = self.plain_text()
        mode = self.mode_combo.currentData()
        if mode == InputMode.AUTO:
            return detect_input(text)
        if mode == InputMode.HANZI:
            return detect_hanzi_only(text)
        return detect_pinyin_only(text)
