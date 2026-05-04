"""Tone-colored syllable breakdown."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

# Tone 1–4 + neutral (tone 5 / unmarked): red, green, blue, purple, gray
TONE_COLORS: dict[int, str] = {
    1: "#c62828",
    2: "#2e7d32",
    3: "#1565c0",
    4: "#6a1b9a",
    5: "#757575",
}


class ToneDisplay(QWidget):
    """Show each syllable with tone number above, color-coded."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 8, 4, 8)
        self._layout.setSpacing(12)
        self._layout.addStretch(1)
        self.clear()

    def clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._layout.addStretch(1)

    def set_syllables(self, syllables: list[str], tones: list[int]) -> None:
        self.clear()
        font_top = QFont()
        font_top.setPointSize(10)
        font_top.setBold(True)
        font_bot = QFont()
        font_bot.setPointSize(14)

        for syl, tone in zip(syllables, tones):
            t = tone if tone in TONE_COLORS else 5
            color = TONE_COLORS.get(t, TONE_COLORS[5])

            cell = QWidget(self)
            v = QVBoxLayout(cell)
            v.setContentsMargins(0, 0, 0, 0)
            lbl_num = QLabel("·" if t >= 5 else str(t))
            lbl_num.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            lbl_num.setFont(font_top)
            lbl_num.setStyleSheet(f"color: {color};")
            lbl_txt = QLabel(syl)
            lbl_txt.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            lbl_txt.setFont(font_bot)
            lbl_txt.setStyleSheet(f"color: {color};")
            v.addWidget(lbl_num)
            v.addWidget(lbl_txt)
            cell.setSizePolicy(
                QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum
            )
            self._layout.insertWidget(self._layout.count() - 1, cell)

        self._layout.addStretch(1)
