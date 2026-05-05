"""Playback speed, voice, transport, syllable list, and save."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.i18n import UiTexts

# Default ~0.9×: calmer than raw 1× for learners (still uses ffmpeg atempo).
SPEED_CHOICES: list[tuple[str, float]] = [
    ("0.25×", 0.25),
    ("0.5×", 0.5),
    ("0.75×", 0.75),
    ("0.9× (default)", 0.9),
    ("1×", 1.0),
    ("1.25×", 1.25),
    ("1.5×", 1.5),
    ("2×", 2.0),
]
DEFAULT_SPEED_INDEX = 3  # 0.9×


class PlaybackPanel(QWidget):
    play_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    save_clicked = pyqtSignal()
    syllable_activated = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.speed_combo = QComboBox()
        for label, val in SPEED_CHOICES:
            self.speed_combo.addItem(label, val)
        self.speed_combo.setCurrentIndex(DEFAULT_SPEED_INDEX)

        self.voice_combo = QComboBox()
        self.voice_combo.setCurrentIndex(0)

        self.btn_play = QPushButton()
        self.btn_stop = QPushButton()
        self.btn_save = QPushButton()
        self.btn_loop = QPushButton()
        self.btn_loop.setCheckable(True)

        for b in (
            self.btn_play,
            self.btn_stop,
            self.btn_save,
            self.btn_loop,
        ):
            b.setMinimumHeight(32)

        row_transport = QHBoxLayout()
        row_transport.addWidget(self.btn_play)
        row_transport.addWidget(self.btn_stop)
        row_transport.addWidget(self.btn_save)
        row_transport.addWidget(self.btn_loop)

        self.syllable_list = QListWidget()
        self.syllable_list.setMinimumHeight(120)
        self.syllable_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.syllable_list.setStyleSheet(
            "QListWidget::item:hover { background-color: rgba(144, 202, 249, 0.15); }"
        )

        self._lbl_speed = QLabel()
        self._lbl_voice = QLabel()
        form = QFormLayout()
        form.addRow(self._lbl_speed, self.speed_combo)
        form.addRow(self._lbl_voice, self.voice_combo)

        self._lbl_syllables = QLabel()
        self._group = QGroupBox()
        v = QVBoxLayout(self._group)
        v.addLayout(form)
        v.addLayout(row_transport)
        v.addWidget(self._lbl_syllables)
        v.addWidget(self.syllable_list, stretch=1)

        outer = QVBoxLayout(self)
        outer.addWidget(self._group)

        self.btn_play.clicked.connect(self.play_clicked.emit)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        self.btn_save.clicked.connect(self.save_clicked.emit)
        self.syllable_list.itemActivated.connect(
            lambda item: self.syllable_activated.emit(self.syllable_list.row(item))
        )
        self.syllable_list.itemClicked.connect(
            lambda item: self.syllable_activated.emit(self.syllable_list.row(item))
        )

    def loop_enabled(self) -> bool:
        return self.btn_loop.isChecked()

    def apply_language(self, t: UiTexts) -> None:
        self._group.setTitle(t.group_playback)
        self._lbl_speed.setText(t.label_speed)
        self._lbl_voice.setText(t.label_voice)
        self._lbl_syllables.setText(t.label_syllables)
        vk = self.voice_combo.currentData()
        self.voice_combo.clear()
        self.voice_combo.addItem(t.voice_female, "female")
        self.voice_combo.addItem(t.voice_male, "male")
        if vk is not None:
            idx = self.voice_combo.findData(vk)
            self.voice_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.btn_play.setText(t.btn_play)
        self.btn_stop.setText(t.btn_stop)
        self.btn_save.setText(t.btn_save)
        self.btn_loop.setText(f"🔁 {t.btn_loop}")

    def current_speed(self) -> float:
        v = self.speed_combo.currentData()
        return float(v) if v is not None else 1.0

    def voice_key(self) -> str:
        key = self.voice_combo.currentData()
        return str(key) if key is not None else "female"

    def set_busy(self, busy: bool) -> None:
        self.btn_play.setEnabled(not busy)
        self.btn_save.setEnabled(not busy)

    def set_syllables(
        self,
        items: list[str],
        hanzi_per_syllable: tuple[str, ...] | None = None,
    ) -> None:
        self.syllable_list.clear()
        hz_row = hanzi_per_syllable or ()
        for i, s in enumerate(items):
            hz = hz_row[i].strip() if i < len(hz_row) else ""
            if hz and len(hz) == 1 and "\u4e00" <= hz <= "\u9fff":
                label = f"{i + 1}. {hz} · {s}"
            elif hz:
                label = f"{i + 1}. {hz} · {s}"
            else:
                label = f"{i + 1}. {s}"
            self.syllable_list.addItem(label)
