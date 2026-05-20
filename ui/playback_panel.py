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

from core.kokoro_tts_engine import list_kokoro_voices
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

TTS_ENGINE_EDGE = "edge"
TTS_ENGINE_KOKORO = "kokoro"


class PlaybackPanel(QWidget):
    play_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    save_clicked = pyqtSignal()
    syllable_activated = pyqtSignal(int)
    tts_settings_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._ui_lang_code = "en"

        self.speed_combo = QComboBox()
        for label, val in SPEED_CHOICES:
            self.speed_combo.addItem(label, val)
        self.speed_combo.setCurrentIndex(DEFAULT_SPEED_INDEX)

        self.engine_combo = QComboBox()
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

        self._lbl_engine = QLabel()
        self._lbl_speed = QLabel()
        self._lbl_voice = QLabel()
        form = QFormLayout()
        form.addRow(self._lbl_engine, self.engine_combo)
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
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        self.voice_combo.currentIndexChanged.connect(self.tts_settings_changed.emit)

    def _on_engine_changed(self, _index: int) -> None:
        from ui.i18n import UiLanguage, texts

        try:
            ul = UiLanguage(self._ui_lang_code)
        except ValueError:
            ul = UiLanguage.EN
        self._fill_voice_combo(texts(ul))
        self.tts_settings_changed.emit()

    def loop_enabled(self) -> bool:
        return self.btn_loop.isChecked()

    def apply_language(self, t: UiTexts, ui_lang_code: str) -> None:
        self._ui_lang_code = ui_lang_code
        self._group.setTitle(t.group_playback)
        self._lbl_engine.setText(t.label_tts_engine)
        self._lbl_speed.setText(t.label_speed)
        self._lbl_voice.setText(t.label_voice)

        prev_engine = self.tts_engine()
        prev_voice = self.voice_key()

        self.engine_combo.blockSignals(True)
        self.engine_combo.clear()
        self.engine_combo.addItem(t.tts_engine_edge, TTS_ENGINE_EDGE)
        self.engine_combo.addItem(t.tts_engine_kokoro, TTS_ENGINE_KOKORO)
        ei = self.engine_combo.findData(prev_engine)
        self.engine_combo.setCurrentIndex(ei if ei >= 0 else 0)
        self.engine_combo.blockSignals(False)

        self._fill_voice_combo(t)
        vi = self.voice_combo.findData(prev_voice)
        if vi >= 0:
            self.voice_combo.blockSignals(True)
            self.voice_combo.setCurrentIndex(vi)
            self.voice_combo.blockSignals(False)

        self.btn_play.setText(t.btn_play)
        self.btn_stop.setText(t.btn_stop)
        self.btn_save.setText(t.btn_save)
        self.btn_loop.setText(f"🔁 {t.btn_loop}")
        self._lbl_syllables.setText(t.label_syllables)

    def set_tts_preferences(self, engine: str, voice_key: str) -> None:
        """Restore from QSettings after ``apply_language`` (no ``tts_settings_changed``)."""
        self.engine_combo.blockSignals(True)
        self.voice_combo.blockSignals(True)
        if engine in (TTS_ENGINE_EDGE, TTS_ENGINE_KOKORO):
            idx = self.engine_combo.findData(engine)
            if idx >= 0:
                self.engine_combo.setCurrentIndex(idx)
        self._fill_voice_combo_from_current_engine()
        vi = self.voice_combo.findData(voice_key)
        if vi >= 0:
            self.voice_combo.setCurrentIndex(vi)
        self.voice_combo.blockSignals(False)
        self.engine_combo.blockSignals(False)

    def _fill_voice_combo(self, t: UiTexts) -> None:
        self.voice_combo.blockSignals(True)
        self.voice_combo.clear()
        eng = self.engine_combo.currentData()
        if eng == TTS_ENGINE_KOKORO:
            for vid, label in list_kokoro_voices(self._ui_lang_code):
                self.voice_combo.addItem(f"🎙️ {label}", vid)
        else:
            self.voice_combo.addItem(t.voice_female, "female")
            self.voice_combo.addItem(t.voice_male, "male")
        self.voice_combo.blockSignals(False)

    def _fill_voice_combo_from_current_engine(self) -> None:
        from ui.i18n import texts
        from ui.i18n import UiLanguage

        try:
            lang = UiLanguage(self._ui_lang_code)
        except ValueError:
            lang = UiLanguage.EN
        self._fill_voice_combo(texts(lang))

    def tts_engine(self) -> str:
        e = self.engine_combo.currentData()
        if e == TTS_ENGINE_KOKORO:
            return TTS_ENGINE_KOKORO
        return TTS_ENGINE_EDGE

    def current_speed(self) -> float:
        v = self.speed_combo.currentData()
        return float(v) if v is not None else 1.0

    def voice_key(self) -> str:
        key = self.voice_combo.currentData()
        if key is not None:
            return str(key)
        return "female"

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
