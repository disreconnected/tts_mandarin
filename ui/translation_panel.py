"""Translation tab: EN<->ZH with pinyin preview and word breakdown cards."""

from __future__ import annotations

import re

import jieba
from pypinyin import Style, lazy_pinyin
from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QEnterEvent, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QFrame,
    QVBoxLayout,
    QWidget,
)

from core.translator import TranslationError, translate_text

_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_WORD_RE = re.compile(r"[A-Za-z0-9\u3400-\u9fff]+")

TONE_COLORS: dict[int, str] = {
    1: "#c62828",
    2: "#2e7d32",
    3: "#1565c0",
    4: "#6a1b9a",
    5: "#757575",
}


def _contains_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text))


def _tone_of_syllable(syl: str) -> int:
    for ch in syl:
        if ch in "āēīōūǖĀĒĪŌŪǕ":
            return 1
        if ch in "áéíóúǘÁÉÍÓÚǗ":
            return 2
        if ch in "ǎěǐǒǔǚǍĚǏǑǓǙ":
            return 3
        if ch in "àèìòùǜÀÈÌÒÙǛ":
            return 4
    return 5


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


class WordCard(QFrame):
    """Small card for Hanzi + Pinyin + English gloss."""

    def __init__(self, hanzi: str, pinyin: str, gloss: str, tone: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._accent = TONE_COLORS.get(tone, TONE_COLORS[5])
        self.setObjectName("wordCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumWidth(100)
        self._apply_style(hover=False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)

        hz = QLabel(hanzi)
        hz_font = QFont("Microsoft YaHei", 20)
        hz_font.setBold(True)
        hz.setFont(hz_font)
        hz.setStyleSheet("color: #f0f0f0;")
        hz.setAlignment(Qt.AlignmentFlag.AlignLeft)

        py = QLabel(pinyin)
        py_font = QFont()
        py_font.setPointSize(12)
        py.setFont(py_font)
        py.setStyleSheet(f"color: {self._accent};")

        en = QLabel(gloss or "—")
        en_font = QFont()
        en_font.setPointSize(10)
        en.setFont(en_font)
        en.setStyleSheet("color: #9e9e9e;")

        lay.addWidget(hz)
        lay.addWidget(py)
        lay.addWidget(en)

    def _apply_style(self, hover: bool) -> None:
        border = self._accent if hover else "#3a3a3a"
        self.setStyleSheet(
            f"QFrame#wordCard {{ background-color: #2a2a2a; border: 1px solid {border}; border-radius: 8px; }}"
        )

    def enterEvent(self, event: QEnterEvent) -> None:
        self._apply_style(hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._apply_style(hover=False)
        super().leaveEvent(event)


class GlossWorker(QObject):
    """Background worker that builds word-by-word cards."""

    finished = pyqtSignal(int, list)
    failed = pyqtSignal(int, str)

    def __init__(self, token: int, chinese_text: str) -> None:
        super().__init__()
        self._token = token
        self._text = chinese_text

    @pyqtSlot()
    def run(self) -> None:
        try:
            words = [w.strip() for w in jieba.cut(self._text) if w.strip()]
            words = [w for w in words if _WORD_RE.fullmatch(w) and _contains_cjk(w)]
            cards: list[tuple[str, str, str, int]] = []
            for w in words:
                pys = lazy_pinyin(
                    w,
                    style=Style.TONE,
                    neutral_tone_with_five=True,
                    tone_sandhi=True,
                    errors=lambda x: list(x),
                )
                pinyin = " ".join(pys).strip()
                tone = _tone_of_syllable(pys[0]) if pys else 5
                try:
                    gloss = translate_text(w, source="zh-CN", target="en")
                except Exception:
                    gloss = ""
                cards.append((w, pinyin, gloss, tone))
            self.finished.emit(self._token, cards)
        except Exception as e:
            self.failed.emit(self._token, str(e))


class TranslationPanel(QWidget):
    """Translate text and optionally send Chinese output to trainer."""

    send_to_trainer = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._result_chinese: str = ""
        self._request_token = 0
        self._worker_thread: QThread | None = None

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
        self._result = QLabel("")
        self._result.setWordWrap(True)
        self._result.setMinimumHeight(120)
        self._result.setStyleSheet("color: #f5f5f5;")
        self._set_result_font(False)

        self._pinyin_label = QLabel("Pinyin:")
        self._pinyin = QLabel("")
        self._pinyin.setWordWrap(True)
        self._pinyin.setStyleSheet("color: #c0c0c0;")

        self._breakdown_label = QLabel("Word Breakdown:")
        self._breakdown_loading = QLabel("")
        self._breakdown_loading.setStyleSheet("color: #9e9e9e;")

        self._breakdown_host = QWidget()
        self._breakdown_layout = QHBoxLayout(self._breakdown_host)
        self._breakdown_layout.setContentsMargins(6, 6, 6, 6)
        self._breakdown_layout.setSpacing(8)
        self._breakdown_layout.addStretch(1)

        self._breakdown_scroll = QScrollArea()
        self._breakdown_scroll.setWidgetResizable(True)
        self._breakdown_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._breakdown_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._breakdown_scroll.setMinimumHeight(170)
        self._breakdown_scroll.setWidget(self._breakdown_host)

        lay.addLayout(form)
        lay.addWidget(self._input)
        lay.addLayout(row)
        lay.addWidget(self._result_label)
        lay.addWidget(self._result)
        lay.addWidget(self._pinyin_label)
        lay.addWidget(self._pinyin)
        lay.addWidget(self._breakdown_label)
        lay.addWidget(self._breakdown_loading)
        lay.addWidget(self._breakdown_scroll)

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
        self._result.setText("")
        self._pinyin.setText("")
        self._clear_breakdown()
        self._breakdown_loading.setText("")

        text = self._input.toPlainText().strip()
        if not text:
            self._result.setText("Please enter text.")
            return
        src, dst = self._resolve_direction(text)
        try:
            translated = translate_text(text, source=src, target=dst)
        except TranslationError as e:
            if e.key == "empty_input":
                self._result.setText("Please enter text.")
            else:
                self._result.setText(f"Translation failed: {e.detail or e.key}")
            return

        if dst.lower().startswith("zh"):
            chinese_text = translated
            self._set_result_font(True)
            self._result.setText(chinese_text)
            self._result_chinese = chinese_text
            self._pinyin.setText(_pinyin_preview(chinese_text))
            self._btn_send.setEnabled(bool(chinese_text.strip()))
            self._start_gloss_worker(chinese_text)
        else:
            self._set_result_font(False)
            self._result.setText(translated)
            source_chinese = text if src.lower().startswith("zh") and _contains_cjk(text) else ""
            self._result_chinese = source_chinese.strip()
            self._pinyin.setText(_pinyin_preview(self._result_chinese))
            self._btn_send.setEnabled(bool(self._result_chinese))
            if self._result_chinese:
                self._start_gloss_worker(self._result_chinese)

    def _on_send(self) -> None:
        chinese = self._result_chinese.strip()
        if chinese:
            self.send_to_trainer.emit(chinese)

    def _set_result_font(self, prefer_hanzi: bool) -> None:
        if prefer_hanzi:
            f = QFont("Microsoft YaHei", 28)
            f.setBold(True)
        else:
            f = QFont()
            f.setPointSize(14)
            f.setBold(False)
        self._result.setFont(f)

    def _clear_breakdown(self) -> None:
        while self._breakdown_layout.count():
            item = self._breakdown_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._breakdown_layout.addStretch(1)

    def _start_gloss_worker(self, chinese_text: str) -> None:
        self._request_token += 1
        token = self._request_token
        self._breakdown_loading.setText("Loading glosses...")
        self._clear_breakdown()

        thread = QThread(self)
        worker = GlossWorker(token, chinese_text)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_gloss_finished)
        worker.failed.connect(self._on_gloss_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._worker_thread = thread
        thread.start()

    @pyqtSlot(int, list)
    def _on_gloss_finished(self, token: int, cards: list) -> None:
        if token != self._request_token:
            return
        self._breakdown_loading.setText("")
        self._clear_breakdown()
        for hanzi, pinyin, gloss, tone in cards:
            self._breakdown_layout.insertWidget(
                self._breakdown_layout.count() - 1,
                WordCard(hanzi, pinyin, gloss, tone, self._breakdown_host),
            )

    @pyqtSlot(int, str)
    def _on_gloss_failed(self, token: int, detail: str) -> None:
        if token != self._request_token:
            return
        self._clear_breakdown()
        self._breakdown_loading.setText(f"Loading glosses failed: {detail}")
