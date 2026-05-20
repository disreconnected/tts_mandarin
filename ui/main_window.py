"""Main PyQt6 window: compose panels, pygame playback, and TTS worker."""

from __future__ import annotations

from pathlib import Path

import pygame
from PyQt6.QtCore import QSettings, QThread, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.audio_processor import AudioProcessingError, export_copy
from core.input_detector import InputDetectionError
from core.pinyin_converter import PreparedPhrase, prepare_phrase
from ui.i18n import (
    UiLanguage,
    format_audio_error,
    format_input_error,
    texts,
)
from ui.input_panel import InputPanel
from ui.playback_panel import TTS_ENGINE_EDGE, TTS_ENGINE_KOKORO, PlaybackPanel
from ui.tone_display import ToneDisplay
from ui.translation_panel import TranslationPanel
from ui.tts_worker import TTSWorker

SETTINGS_ORG = "TTSMandarin"
SETTINGS_APP = "ChinesePronunciationTrainer"
SETTINGS_LANG_KEY = "ui/language"
SETTINGS_TTS_ENGINE = "tts/engine"
SETTINGS_TTS_VOICE = "tts/voice"

# Advance highlight so the UI leads the ear. TTS does not space syllables evenly, so mid-phrase
# syllables (e.g. 几 in 你家有几口人) can feel late with a fixed lead — add a small ramp toward
# the end of the clip on top of the base lead.
HIGHLIGHT_LEAD_MS = 170
HIGHLIGHT_PROGRESSIVE_MAX_MS = 52


def _wav_duration_seconds(path: Path) -> float:
    """Length of ``path`` in seconds (pygame first, then pydub)."""
    try:
        return float(pygame.mixer.Sound(str(path)).get_length())
    except Exception:
        pass
    try:
        from pydub import AudioSegment

        return float(len(AudioSegment.from_file(str(path))) / 1000.0)
    except Exception:
        return 0.0


def _avg_syllable_duration_sec(wav_path: Path, syllable_count: int) -> float:
    """Seconds per syllable from the final (speed-adjusted) WAV."""
    n = max(1, syllable_count)
    total = _wav_duration_seconds(wav_path)
    if total > 0:
        return total / n
    return max(0.12, 0.35 / n)


class MainWindow(QMainWindow):
    tts_request = pyqtSignal(str, str, str, float, str, bool, str)

    def __init__(self, base_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(1100, 700)
        self.resize(1200, 800)
        self._base_dir = base_dir
        self._temp_dir = base_dir / "temp_audio"
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._history_path = base_dir / "assets" / "history.json"

        self._settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._ui_lang = self._read_saved_language()

        pygame.mixer.init(frequency=44100)
        self._prepared: PreparedPhrase | None = None
        self._cached_mp3: str | None = None
        self._cache_key: tuple[str, str, str] | None = None
        self._current_wav: Path | None = None
        self._pending_voice_key: str = "female"
        self._pending_tts_engine: str = TTS_ENGINE_EDGE
        self._busy = False

        self._pending_syllable_index: int | None = None
        self._pending_was_full_phrase = False
        self._transport_active = False
        self._loop_armed = False
        self._syllable_duration_sec = 0.35
        self._playback_total_ms = 0.0
        self._highlight_mode_full = True
        self._highlight_single_idx: int | None = None
        self._highlight_syllable_count = 0

        self._highlight_timer = QTimer(self)
        self._highlight_timer.setInterval(100)
        self._highlight_timer.timeout.connect(self._on_highlight_tick)

        self._playback_monitor_timer = QTimer(self)
        self._playback_monitor_timer.setInterval(150)
        self._playback_monitor_timer.timeout.connect(self._on_playback_monitor_tick)

        self._tts_thread = QThread(self)
        self._tts_worker = TTSWorker(self._temp_dir, self._base_dir)
        self._tts_worker.moveToThread(self._tts_thread)
        self.tts_request.connect(
            self._tts_worker.synthesize,
            Qt.ConnectionType.QueuedConnection,
        )
        self._tts_worker.finished.connect(self._on_tts_finished)
        self._tts_worker.failed.connect(self._on_tts_failed)
        self._tts_thread.start()

        self._input = InputPanel(self._history_path)
        self._tone_display = ToneDisplay()

        self._playback = PlaybackPanel()

        right_split = QSplitter(Qt.Orientation.Vertical)
        right_split.addWidget(self._tone_display)
        right_split.addWidget(self._playback)
        right_split.setStretchFactor(0, 1)
        right_split.setStretchFactor(1, 2)

        trainer_split = QSplitter(Qt.Orientation.Horizontal)
        trainer_split.addWidget(self._input)
        trainer_split.addWidget(right_split)
        trainer_split.setStretchFactor(0, 1)
        trainer_split.setStretchFactor(1, 2)

        trainer_tab = QWidget()
        trainer_lay = QVBoxLayout(trainer_tab)
        trainer_lay.setContentsMargins(0, 0, 0, 0)
        trainer_lay.addWidget(trainer_split)

        self._translation = TranslationPanel()
        self._translation.send_to_trainer.connect(self._on_send_to_trainer)

        self._tabs = QTabWidget()
        self._tabs.addTab(trainer_tab, "Trainer")
        self._tabs.addTab(self._translation, "Translation")

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.addWidget(self._tabs)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

        self._setup_language_menu()
        self._setup_shortcuts()
        self._apply_ui_language(self._ui_lang, persist=False)
        self._restore_tts_preferences()

        self._playback.play_clicked.connect(self._on_play)
        self._playback.stop_clicked.connect(self._on_stop)
        self._playback.save_clicked.connect(self._on_save)
        self._playback.syllable_activated.connect(self._on_syllable)
        self._playback.tts_settings_changed.connect(self._on_playback_tts_settings_changed)

    def _setup_shortcuts(self) -> None:
        sc_space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        sc_space.setContext(Qt.ShortcutContext.ApplicationShortcut)
        sc_space.activated.connect(self._shortcut_space_play_stop)

        sc_r = QShortcut(QKeySequence(Qt.Key.Key_R), self)
        sc_r.setContext(Qt.ShortcutContext.ApplicationShortcut)
        sc_r.activated.connect(self._shortcut_replay)

        sc_s = QShortcut(QKeySequence(Qt.Key.Key_S), self)
        sc_s.setContext(Qt.ShortcutContext.ApplicationShortcut)
        sc_s.activated.connect(self._shortcut_focus_input)

    def _input_has_focus(self) -> bool:
        fw = QApplication.focusWidget()
        return isinstance(fw, QPlainTextEdit) and fw is self._input.text_edit

    def _shortcut_space_play_stop(self) -> None:
        if self._input_has_focus():
            return
        if pygame.mixer.music.get_busy():
            self._on_stop()
        else:
            self._on_play()

    def _shortcut_replay(self) -> None:
        if self._input_has_focus():
            return
        self._on_replay_resynthesize()

    def _shortcut_focus_input(self) -> None:
        if self._input_has_focus():
            return
        self._input.text_edit.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _read_saved_language(self) -> UiLanguage:
        raw = self._settings.value(SETTINGS_LANG_KEY, UiLanguage.EN.value)
        try:
            return UiLanguage(str(raw))
        except ValueError:
            return UiLanguage.EN

    def _setup_language_menu(self) -> None:
        menu = self.menuBar().addMenu("")
        self._menu_language = menu

        self._act_lang_en = QAction("", self)
        self._act_lang_en.setCheckable(True)
        self._act_lang_zh = QAction("", self)
        self._act_lang_zh.setCheckable(True)

        group = QActionGroup(self)
        group.setExclusive(True)
        group.addAction(self._act_lang_en)
        group.addAction(self._act_lang_zh)

        menu.addAction(self._act_lang_en)
        menu.addAction(self._act_lang_zh)

        self._act_lang_en.triggered.connect(
            lambda: self._apply_ui_language(UiLanguage.EN, persist=True)
        )
        self._act_lang_zh.triggered.connect(
            lambda: self._apply_ui_language(UiLanguage.ZH, persist=True)
        )

    def _apply_ui_language(self, lang: UiLanguage, *, persist: bool) -> None:
        self._ui_lang = lang
        if persist:
            self._settings.setValue(SETTINGS_LANG_KEY, lang.value)

        t = texts(lang)
        self._menu_language.setTitle(t.menu_language)
        self._act_lang_en.setText(t.lang_english)
        self._act_lang_zh.setText(t.lang_chinese)
        self.setWindowTitle(t.window_title)
        self._tabs.setTabText(0, t.tab_trainer)
        self._tabs.setTabText(1, t.tab_translation)
        self._input.apply_language(t)
        self._playback.apply_language(t, lang.value)
        self._tone_display.set_ui_language(lang)
        self._act_lang_en.setChecked(lang == UiLanguage.EN)
        self._act_lang_zh.setChecked(lang == UiLanguage.ZH)
        self._show_status_idle()
        if self._prepared is not None:
            self._refresh_phrase_ui(self._prepared)

    def _restore_tts_preferences(self) -> None:
        raw_e = self._settings.value(SETTINGS_TTS_ENGINE, TTS_ENGINE_EDGE)
        engine = (
            str(raw_e)
            if str(raw_e) in (TTS_ENGINE_EDGE, TTS_ENGINE_KOKORO)
            else TTS_ENGINE_EDGE
        )
        voice = str(self._settings.value(SETTINGS_TTS_VOICE, "female"))
        self._playback.set_tts_preferences(engine, voice)

    def _on_playback_tts_settings_changed(self) -> None:
        self._cache_key = None
        self._cached_mp3 = None
        self._settings.setValue(SETTINGS_TTS_ENGINE, self._playback.tts_engine())
        self._settings.setValue(SETTINGS_TTS_VOICE, self._playback.voice_key())

    def _show_status_idle(self) -> None:
        t = texts(self._ui_lang)
        self.statusBar().showMessage(f"{t.status_ready} — {t.status_shortcuts_hint}")

    def _t(self):
        return texts(self._ui_lang)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._stop_transport()
        self._cleanup_temp()
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        self._tts_thread.quit()
        self._tts_thread.wait(3000)
        super().closeEvent(event)

    def _cleanup_temp(self) -> None:
        if not self._temp_dir.is_dir():
            return
        for p in self._temp_dir.iterdir():
            try:
                if p.is_file():
                    p.unlink()
            except OSError:
                pass

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._playback.set_busy(busy)

    def _stop_transport(self) -> None:
        self._transport_active = False
        self._loop_armed = False
        self._highlight_timer.stop()
        self._playback_monitor_timer.stop()
        self._tone_display.highlight(None)

    def _prepare_from_input(self) -> PreparedPhrase:
        detection = self._input.detect()
        return prepare_phrase(detection)

    def _refresh_phrase_ui(self, prepared: PreparedPhrase) -> None:
        self._tone_display.setUpdatesEnabled(False)
        self._tone_display.set_phrase(
            prepared.syllables,
            prepared.syllable_tones,
            prepared.hanzi_per_syllable,
        )
        self._tone_display.setUpdatesEnabled(True)
        self._playback.set_syllables(
            prepared.syllables,
            prepared.hanzi_per_syllable,
        )

    @staticmethod
    def _tts_text_for_syllable(prepared: PreparedPhrase, index: int) -> str:
        """Prefer one Hanzi character for zh-CN TTS; Latin pinyin sounds unnatural in isolation."""
        if 0 <= index < len(prepared.hanzi_per_syllable):
            h = prepared.hanzi_per_syllable[index].strip()
            if len(h) == 1 and "\u4e00" <= h <= "\u9fff":
                return h
        return prepared.syllables[index]

    def _on_play(self) -> None:
        if self._busy:
            return
        t = self._t()
        try:
            prepared = self._prepare_from_input()
        except InputDetectionError as e:
            QMessageBox.warning(self, t.dlg_invalid_input, format_input_error(self._ui_lang, e))
            return
        except Exception as e:
            QMessageBox.critical(self, t.dlg_error, str(e))
            return

        self._prepared = prepared
        self._refresh_phrase_ui(prepared)
        self._run_synthesis(prepared.tts_text, syllable=None, syllable_index=None)

    def _on_replay_resynthesize(self) -> None:
        """Re-run Edge-TTS with current box text and playback settings (R shortcut)."""
        if self._busy:
            return
        t = self._t()
        try:
            prepared = self._prepare_from_input()
        except InputDetectionError as e:
            QMessageBox.warning(self, t.dlg_invalid_input, format_input_error(self._ui_lang, e))
            return
        except Exception as e:
            QMessageBox.critical(self, t.dlg_error, str(e))
            return
        self._prepared = prepared
        self._refresh_phrase_ui(prepared)
        self._cache_key = None
        self._cached_mp3 = None
        self._run_synthesis(prepared.tts_text, syllable=None, syllable_index=None)

    def _run_synthesis(
        self,
        tts_text: str,
        *,
        syllable: str | None,
        syllable_index: int | None = None,
    ) -> None:
        if self._busy:
            return
        t = self._t()
        prepared = self._prepared
        if prepared is None:
            try:
                prepared = self._prepare_from_input()
                self._prepared = prepared
                self._refresh_phrase_ui(prepared)
            except InputDetectionError as e:
                QMessageBox.warning(
                    self, t.dlg_invalid_input, format_input_error(self._ui_lang, e)
                )
                return

        self._pending_syllable_index = syllable_index
        self._pending_was_full_phrase = syllable_index is None and syllable is None

        if syllable_index is not None:
            text = self._tts_text_for_syllable(prepared, syllable_index)
        elif syllable is not None:
            text = syllable
        else:
            text = tts_text
        voice_key = self._playback.voice_key()
        engine = self._playback.tts_engine()
        speed = self._playback.current_speed()
        self._pending_voice_key = voice_key
        self._pending_tts_engine = engine

        reuse = ""
        should_update_cache = syllable is None and syllable_index is None
        if should_update_cache:
            key = (prepared.tts_text, engine, voice_key)
            if (
                self._cache_key == key
                and self._cached_mp3
                and Path(self._cached_mp3).is_file()
            ):
                reuse = self._cached_mp3
                should_update_cache = False

        self._set_busy(True)
        self.statusBar().showMessage(t.status_synthesizing)
        self.tts_request.emit(
            text,
            engine,
            voice_key,
            speed,
            reuse,
            should_update_cache,
            self._ui_lang.value,
        )

    def _on_tts_finished(self, wav: str, mp3: str, should_update_cache: bool) -> None:
        self._set_busy(False)
        t = self._t()
        if should_update_cache and self._prepared is not None:
            self._cached_mp3 = mp3
            self._cache_key = (
                self._prepared.tts_text,
                self._pending_tts_engine,
                self._pending_voice_key,
            )

        if self._pending_was_full_phrase:
            self._input.record_successful_play(self._input.plain_text())

        self._current_wav = Path(wav)
        try:
            pygame.mixer.music.load(wav)
            pygame.mixer.music.play()
            self.statusBar().showMessage(
                f"{t.status_playing} — {t.status_shortcuts_hint}"
            )
        except Exception as e:
            QMessageBox.warning(self, t.dlg_playback_failed, str(e))
            self._show_status_idle()
            return

        prepared = self._prepared
        if prepared is None:
            self._stop_transport()
            return

        idx = self._pending_syllable_index
        if idx is not None:
            self._highlight_mode_full = False
            self._highlight_single_idx = idx
            self._highlight_syllable_count = 1
        else:
            self._highlight_mode_full = True
            self._highlight_single_idx = None
            self._highlight_syllable_count = max(1, len(prepared.syllables))

        self._syllable_duration_sec = _avg_syllable_duration_sec(
            self._current_wav,
            self._highlight_syllable_count,
        )
        self._playback_total_ms = (
            self._syllable_duration_sec * float(self._highlight_syllable_count) * 1000.0
        )
        self._loop_armed = self._playback.loop_enabled()
        self._transport_active = True
        self._highlight_timer.start()
        self._playback_monitor_timer.start()

    def _on_tts_failed(self, message: str) -> None:
        self._set_busy(False)
        t = self._t()
        self._show_status_idle()
        QMessageBox.warning(self, t.dlg_synthesis_failed, message)

    def _on_highlight_tick(self) -> None:
        if not self._transport_active or not pygame.mixer.music.get_busy():
            return
        if not self._highlight_mode_full and self._highlight_single_idx is not None:
            self._tone_display.highlight(self._highlight_single_idx)
            return
        n = self._highlight_syllable_count
        if n <= 0:
            return
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms < 0:
            pos_ms = 0
        step_ms = self._syllable_duration_sec * 1000.0
        if step_ms <= 0:
            return
        total_ms = max(self._playback_total_ms, 1.0)
        progressive = HIGHLIGHT_PROGRESSIVE_MAX_MS * (float(pos_ms) / total_ms)
        effective_ms = float(pos_ms) + float(HIGHLIGHT_LEAD_MS) + progressive
        idx = int(effective_ms / step_ms)
        idx = min(n - 1, max(0, idx))
        self._tone_display.highlight(idx)

    def _on_playback_monitor_tick(self) -> None:
        if not self._transport_active:
            return
        if pygame.mixer.music.get_busy():
            return
        self._highlight_timer.stop()
        self._playback_monitor_timer.stop()
        self._tone_display.highlight(None)
        if self._playback.loop_enabled() and self._loop_armed:
            try:
                pygame.mixer.music.rewind()
                pygame.mixer.music.play()
                self._highlight_timer.start()
                self._playback_monitor_timer.start()
                self.statusBar().showMessage(
                    f"{self._t().status_playing} — {self._t().status_shortcuts_hint}"
                )
            except Exception:
                self._transport_active = False
                self._loop_armed = False
                self._show_status_idle()
        else:
            self._transport_active = False
            self._loop_armed = False
            self._show_status_idle()

    def _on_stop(self) -> None:
        pygame.mixer.music.stop()
        self._stop_transport()
        t = self._t()
        self.statusBar().showMessage(f"{t.status_stopped} — {t.status_shortcuts_hint}")

    def _on_save(self) -> None:
        t = self._t()
        path, _ = QFileDialog.getSaveFileName(
            self,
            t.dlg_save_audio,
            str(self._base_dir / "pronunciation.wav"),
            "WAV (*.wav);;MP3 (*.mp3)",
        )
        if not path:
            return
        src = self._current_wav
        if src is None or not src.is_file():
            QMessageBox.information(self, t.dlg_save, t.dlg_save_nothing)
            return
        dest = Path(path)
        try:
            ext = dest.suffix.lower().lstrip(".")
            fmt = ext if ext in ("wav", "mp3") else "wav"
            export_copy(src, dest, format_hint=fmt)
            self.statusBar().showMessage(t.status_saved.format(path=str(dest)))
        except AudioProcessingError as e:
            QMessageBox.warning(
                self, t.dlg_save_failed, format_audio_error(self._ui_lang, e)
            )
        except Exception as e:
            QMessageBox.warning(self, t.dlg_save_failed, str(e))

    def _on_syllable(self, index: int) -> None:
        prepared = self._prepared
        if prepared is None or index < 0 or index >= len(prepared.syllables):
            return
        self._run_synthesis(
            prepared.tts_text,
            syllable=None,
            syllable_index=index,
        )

    def _on_send_to_trainer(self, chinese_text: str) -> None:
        self._tabs.setCurrentIndex(0)
        self._input.set_plain_text(chinese_text)
        self._input.text_edit.setFocus(Qt.FocusReason.OtherFocusReason)
        self._on_play()
