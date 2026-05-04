"""Tone-colored syllable breakdown (Hanzi + tone + Pinyin)."""

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
    """Show Hanzi (when available), tone mark, and Pinyin per syllable — left-aligned, compact."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(10)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.clear()

    def clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def set_phrase(
        self,
        syllables: list[str],
        tones: list[int],
        hanzi_per_syllable: tuple[str, ...] | None = None,
    ) -> None:
        self.clear()
        hanzi_row = hanzi_per_syllable or tuple()
        show_hanzi = (
            len(syllables) > 0 and len(hanzi_row) == len(syllables)
        )

        font_hz = QFont()
        font_hz.setPointSize(26)
        font_hz.setBold(True)
        font_top = QFont()
        font_top.setPointSize(12)
        font_top.setBold(True)
        font_bot = QFont()
        font_bot.setPointSize(18)
        font_bot.setBold(False)

        for i, (syl, tone) in enumerate(zip(syllables, tones)):
            t = tone if tone in TONE_COLORS else 5
            color = TONE_COLORS.get(t, TONE_COLORS[5])
            hz = hanzi_row[i] if i < len(hanzi_row) else ""
            has_char = bool(hz.strip())
            display_hz = hz.strip() or "·"
            placeholder = not has_char
            hz_color = "#757575" if placeholder else color

            cell = QWidget(self)
            v = QVBoxLayout(cell)
            v.setContentsMargins(4, 0, 4, 0)
            v.setSpacing(2)

            lbl_hz = QLabel(display_hz if show_hanzi else "")
            lbl_hz.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            lbl_hz.setFont(font_hz)
            lbl_hz.setStyleSheet(f"color: {hz_color};")

            lbl_num = QLabel("·" if t >= 5 else str(t))
            lbl_num.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            lbl_num.setFont(font_top)
            lbl_num.setStyleSheet(f"color: {color};")

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
            self._layout.addWidget(cell)

        self._layout.addStretch(1)
