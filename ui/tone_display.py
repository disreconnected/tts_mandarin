"""Tone-colored syllable breakdown (Hanzi + tone + Pinyin)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QMouseEvent, QResizeEvent
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.i18n import UiLanguage

# Tone 1–4 + neutral (tone 5 / unmarked): red, green, blue, purple, gray
TONE_COLORS: dict[int, str] = {
    1: "#c62828",
    2: "#2e7d32",
    3: "#1565c0",
    4: "#6a1b9a",
    5: "#757575",
}

_TONE_GUIDE: dict[UiLanguage, dict[int, tuple[str, str]]] = {
    UiLanguage.EN: {
        1: (
            "Tone 1 — High level",
            "Flat, high pitch. Hold the note steady.\n\n"
            'Mnemonic: flat and high, like saying “aaah” at the doctor.',
        ),
        2: (
            "Tone 2 — Rising",
            "Start mid pitch and rise high.\n\n"
            "Mnemonic: like asking a question in English.",
        ),
        3: (
            "Tone 3 — Dipping",
            "Dip down, then rise a little.\n\n"
            'Mnemonic: like saying “really?” skeptically.',
        ),
        4: (
            "Tone 4 — Falling",
            "Starts high and drops sharply.\n\n"
            "Mnemonic: like giving a firm command.",
        ),
        5: (
            "Neutral tone",
            "Short and light; unstressed compared to full tones.\n\n"
            "Mnemonic: barely pronounced, trailing off lightly.",
        ),
    },
    UiLanguage.ZH: {
        1: (
            "第一声 — 阴平（高平）",
            "音高较高且平稳。\n\n"
            "记忆提示：像看医生时拉长声的“啊——”，音高保持不变。",
        ),
        2: (
            "第二声 — 阳平（升调）",
            "从中音升到高音。\n\n"
            "记忆提示：像英语里句末升调的疑问语气。",
        ),
        3: (
            "第三声 — 上声（降升）",
            "先略降再扬起。\n\n"
            "记忆提示：像略带怀疑的“真的吗？”。",
        ),
        4: (
            "第四声 — 去声（降调）",
            "从高快速落下。\n\n"
            "记忆提示：像短促有力的命令口吻。",
        ),
        5: (
            "轻声",
            "短而弱，相对其他声调不那么用力。\n\n"
            "记忆提示：轻轻带过即可。",
        ),
    },
}


def _show_tone_guide_dialog(tone: int, lang: UiLanguage, parent: QWidget | None) -> None:
    t = tone if tone in _TONE_GUIDE[lang] else 5
    title, body = _TONE_GUIDE[lang][t]
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setModal(True)
    lay = QVBoxLayout(dlg)
    lbl = QLabel(body)
    lbl.setWordWrap(True)
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    lay.addWidget(lbl)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    box.accepted.connect(dlg.accept)
    lay.addWidget(box)
    dlg.exec()


class ClickableToneLabel(QLabel):
    """Tone number row: click opens a short tone guide."""

    def __init__(self, tone_key: int, ui_lang: UiLanguage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tone_key = tone_key
        self._ui_lang = ui_lang
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_ui_language(self, lang: UiLanguage) -> None:
        self._ui_lang = lang

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            _show_tone_guide_dialog(self._tone_key, self._ui_lang, self.window())
        super().mousePressEvent(ev)


class ToneDisplay(QWidget):
    """Show Hanzi (when available), tone mark, and Pinyin per syllable — left-aligned, compact."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setHorizontalSpacing(10)
        self._layout.setVerticalSpacing(8)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._cells: list[QFrame] = []
        self._ui_lang = UiLanguage.EN
        self._highlight_index: int | None = None
        self._syllables: list[str] = []
        self._tones: list[int] = []
        self._hanzi_row: tuple[str, ...] = ()
        self.clear()

    def set_ui_language(self, lang: UiLanguage) -> None:
        self._ui_lang = lang
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if w is None:
                continue
            for child in w.findChildren(ClickableToneLabel):
                child.set_ui_language(lang)

    def clear(self) -> None:
        self._cells.clear()
        self._highlight_index = None
        self._syllables = []
        self._tones = []
        self._hanzi_row = ()
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _column_count(self, n: int) -> int:
        if n <= 0:
            return 1
        w = max(320, self.width())
        target_cell = 115
        return max(1, w // target_cell)

    def _font_sizes(self, n: int) -> tuple[int, int, int]:
        cols = self._column_count(max(1, n))
        per_cell = max(72, (max(320, self.width()) - 24) // cols)
        hz = max(18, min(30, int(per_cell * 0.28)))
        tone = max(10, min(13, int(hz * 0.42)))
        py = max(13, min(20, int(hz * 0.64)))
        return hz, tone, py

    def highlight(self, index: int | None) -> None:
        """Mark syllable ``index`` visually, or ``None`` / negative to clear."""
        self._highlight_index = index if index is not None and index >= 0 else None
        for i, frame in enumerate(self._cells):
            if self._highlight_index is not None and i == self._highlight_index:
                frame.setStyleSheet(
                    "QFrame#toneCell { border: 2px solid #90caf9; border-radius: 8px; "
                    "background-color: rgba(144, 202, 249, 0.14); }"
                )
            else:
                frame.setStyleSheet(
                    "QFrame#toneCell { border: 2px solid transparent; border-radius: 8px; "
                    "background-color: transparent; }"
                )

    def _rebuild_cells(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._cells.clear()

        syllables = self._syllables
        tones = self._tones
        hanzi_row = self._hanzi_row
        show_hanzi = len(syllables) > 0 and len(hanzi_row) == len(syllables)
        font_hz = QFont()
        hz_sz, tone_sz, py_sz = self._font_sizes(len(syllables))
        font_hz.setPointSize(hz_sz)
        font_hz.setBold(True)
        font_top = QFont()
        font_top.setPointSize(tone_sz)
        font_top.setBold(True)
        font_bot = QFont()
        font_bot.setPointSize(py_sz)
        font_bot.setBold(False)

        cols = self._column_count(len(syllables))
        for i, (syl, tone) in enumerate(zip(syllables, tones)):
            t = tone if tone in TONE_COLORS else 5
            color = TONE_COLORS.get(t, TONE_COLORS[5])
            hz = hanzi_row[i] if i < len(hanzi_row) else ""
            has_char = bool(hz.strip())
            display_hz = hz.strip() or "·"
            placeholder = not has_char
            hz_color = "#757575" if placeholder else color

            cell = QFrame(self)
            cell.setObjectName("toneCell")
            v = QVBoxLayout(cell)
            v.setContentsMargins(6, 4, 6, 4)
            v.setSpacing(2)

            lbl_hz = QLabel(display_hz if show_hanzi else "")
            lbl_hz.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            lbl_hz.setFont(font_hz)
            lbl_hz.setStyleSheet(f"color: {hz_color};")

            lbl_num = ClickableToneLabel(t, self._ui_lang, cell)
            lbl_num.setText("·" if t >= 5 else str(t))
            lbl_num.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            lbl_num.setFont(font_top)
            lbl_num.setStyleSheet(f"color: {color}; text-decoration: underline;")

            lbl_txt = QLabel(syl)
            lbl_txt.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            lbl_txt.setFont(font_bot)
            lbl_txt.setStyleSheet(f"color: {color};")

            if show_hanzi:
                v.addWidget(lbl_hz)
            v.addWidget(lbl_num)
            v.addWidget(lbl_txt)
            cell.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum
            )
            self._cells.append(cell)
            row = i // cols
            col = i % cols
            self._layout.addWidget(cell, row, col)
        self.highlight(None)

    def set_phrase(
        self,
        syllables: list[str],
        tones: list[int],
        hanzi_per_syllable: tuple[str, ...] | None = None,
    ) -> None:
        self._syllables = list(syllables)
        self._tones = list(tones)
        self._hanzi_row = hanzi_per_syllable or tuple()
        self._highlight_index = None
        self._rebuild_cells()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._syllables:
            keep = self._highlight_index
            self._rebuild_cells()
            if keep is not None:
                self.highlight(keep)
