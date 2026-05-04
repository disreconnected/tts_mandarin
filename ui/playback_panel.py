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
    QVBoxLayout,
    QWidget,
)

from ui.i18n import UiTexts

SPEED_CHOICES: list[tuple[str, float]] = [
    ("0.25×", 0.25),
    ("0.5×", 0.5),
    ("1×", 1.0),
    ("1.5×", 1.5),
    ("2×", 2.0),
]


class PlaybackPanel(QWidget):
    play_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    replay_clicked = pyqtSignal()
    save_clicked = pyqtSignal()
    syllable_activated = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.speed_combo = QComboBox()
        for label, val in SPEED_CHOICES:
            self.speed_combo.addItem(label, val)
        self.speed_combo.setCurrentIndex(2)  # 1×

        self.voice_combo = QComboBox()
        self.voice_combo.setCurrentIndex(0)

        self.btn_play = QPushButton()
        self.btn_pause = QPushButton()
        self.btn_stop = QPushButton()
        self.btn_replay = QPushButton()
        self.btn_save = QPushButton()

        for b in (
            self.btn_play,
            self.btn_pause,
            self.btn_stop,
            self.btn_replay,
            self.btn_save,
        ):
            b.setMinimumHeight(32)

        row_transport = QHBoxLayout()
        row_transport.addWidget(self.btn_play)
        row_transport.addWidget(self.btn_pause)
        row_transport.addWidget(self.btn_stop)
        row_transport.addWidget(self.btn_replay)
        row_transport.addWidget(self.btn_save)

        self.syllable_list = QListWidget()
        self.syllable_list.setMaximumHeight(120)

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
        v.addWidget(self.syllable_list)

        outer = QVBoxLayout(self)
        outer.addWidget(self._group)

        self.btn_play.clicked.connect(self.play_clicked.emit)
        self.btn_pause.clicked.connect(self.pause_clicked.emit)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        self.btn_replay.clicked.connect(self.replay_clicked.emit)
        self.btn_save.clicked.connect(self.save_clicked.emit)
        self.syllable_list.itemActivated.connect(
            lambda item: self.syllable_activated.emit(self.syllable_list.row(item))
        )
        self.syllable_list.itemClicked.connect(
            lambda item: self.syllable_activated.emit(self.syllable_list.row(item))
        )

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
        self.btn_pause.setText(t.btn_pause)
        self.btn_stop.setText(t.btn_stop)
        self.btn_replay.setText(t.btn_replay)
        self.btn_save.setText(t.btn_save)

    def current_speed(self) -> float:
        v = self.speed_combo.currentData()
        return float(v) if v is not None else 1.0

    def voice_key(self) -> str:
        key = self.voice_combo.currentData()
        return str(key) if key is not None else "female"

    def set_busy(self, busy: bool) -> None:
        self.btn_play.setEnabled(not busy)
        self.btn_save.setEnabled(not busy)

    def set_syllables(self, items: list[str]) -> None:
        self.syllable_list.clear()
        for i, s in enumerate(items):
            self.syllable_list.addItem(f"{i + 1}. {s}")
