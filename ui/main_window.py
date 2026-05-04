"""Main PyQt6 window: compose panels, pygame playback, and TTS worker."""

from __future__ import annotations

from pathlib import Path

import pygame
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.audio_processor import AudioProcessingError, export_copy
from core.input_detector import InputDetectionError
from core.pinyin_converter import PreparedPhrase, prepare_phrase
from ui.input_panel import InputPanel
from ui.playback_panel import PlaybackPanel
from ui.tone_display import ToneDisplay
from ui.tts_worker import TTSWorker


class MainWindow(QMainWindow):
    tts_request = pyqtSignal(str, str, float, str, bool)

    def __init__(self, base_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Chinese Pronunciation Trainer")
        self._base_dir = base_dir
        self._temp_dir = base_dir / "temp_audio"
        self._temp_dir.mkdir(parents=True, exist_ok=True)

        pygame.mixer.init(frequency=44100)
        self._prepared: PreparedPhrase | None = None
        self._cached_mp3: str | None = None
        self._cache_key: tuple[str, str] | None = None
        self._current_wav: Path | None = None
        self._pending_voice_key: str = "female"
        self._busy = False

        self._tts_thread = QThread(self)
        self._tts_worker = TTSWorker(self._temp_dir)
        self._tts_worker.moveToThread(self._tts_thread)
        self.tts_request.connect(
            self._tts_worker.synthesize,
            Qt.ConnectionType.QueuedConnection,
        )
        self._tts_worker.finished.connect(self._on_tts_finished)
        self._tts_worker.failed.connect(self._on_tts_failed)
        self._tts_thread.start()

        self._input = InputPanel()
        self._tone_display = ToneDisplay()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._tone_display)

        self._playback = PlaybackPanel()

        right_split = QSplitter(Qt.Orientation.Vertical)
        right_split.addWidget(scroll)
        right_split.addWidget(self._playback)
        right_split.setStretchFactor(0, 2)
        right_split.setStretchFactor(1, 1)

        main_split = QSplitter(Qt.Orientation.Horizontal)
        main_split.addWidget(self._input)
        main_split.addWidget(right_split)
        main_split.setStretchFactor(0, 1)
        main_split.setStretchFactor(1, 2)

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.addWidget(main_split)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

        self._playback.play_clicked.connect(self._on_play)
        self._playback.pause_clicked.connect(self._on_pause)
        self._playback.stop_clicked.connect(self._on_stop)
        self._playback.replay_clicked.connect(self._on_replay)
        self._playback.save_clicked.connect(self._on_save)
        self._playback.syllable_activated.connect(self._on_syllable)

    def closeEvent(self, event) -> None:  # type: ignore[override]
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

    def _prepare_from_input(self) -> PreparedPhrase:
        detection = self._input.detect()
        return prepare_phrase(detection)

    def _refresh_phrase_ui(self, prepared: PreparedPhrase) -> None:
        self._tone_display.set_syllables(prepared.syllables, prepared.syllable_tones)
        self._playback.set_syllables(prepared.syllables)

    def _on_play(self) -> None:
        if self._busy:
            return
        try:
            prepared = self._prepare_from_input()
        except InputDetectionError as e:
            QMessageBox.warning(self, "输入无效", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
            return

        self._prepared = prepared
        self._refresh_phrase_ui(prepared)
        self._run_synthesis(prepared.tts_text, syllable=None)

    def _run_synthesis(self, tts_text: str, *, syllable: str | None) -> None:
        if self._busy:
            return
        prepared = self._prepared
        if prepared is None:
            try:
                prepared = self._prepare_from_input()
                self._prepared = prepared
                self._refresh_phrase_ui(prepared)
            except InputDetectionError as e:
                QMessageBox.warning(self, "输入无效", str(e))
                return

        text = syllable if syllable is not None else prepared.tts_text
        voice_key = self._playback.voice_key()
        speed = self._playback.current_speed()
        self._pending_voice_key = voice_key

        reuse = ""
        should_update_cache = syllable is None
        if syllable is None:
            key = (prepared.tts_text, voice_key)
            if (
                self._cache_key == key
                and self._cached_mp3
                and Path(self._cached_mp3).is_file()
            ):
                reuse = self._cached_mp3
                should_update_cache = False

        self._set_busy(True)
        self.statusBar().showMessage("正在合成语音…")
        self.tts_request.emit(text, voice_key, speed, reuse, should_update_cache)

    def _on_tts_finished(self, wav: str, mp3: str, should_update_cache: bool) -> None:
        self._set_busy(False)
        if should_update_cache and self._prepared is not None:
            self._cached_mp3 = mp3
            self._cache_key = (self._prepared.tts_text, self._pending_voice_key)

        self._current_wav = Path(wav)
        try:
            pygame.mixer.music.load(wav)
            pygame.mixer.music.play()
            self.statusBar().showMessage("正在播放")
        except Exception as e:
            QMessageBox.warning(self, "播放失败", str(e))

    def _on_tts_failed(self, message: str) -> None:
        self._set_busy(False)
        self.statusBar().showMessage("就绪")
        QMessageBox.warning(self, "合成失败", message)

    def _on_pause(self) -> None:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.statusBar().showMessage("已暂停")
        else:
            try:
                pygame.mixer.music.unpause()
                self.statusBar().showMessage("正在播放")
            except Exception:
                pass

    def _on_stop(self) -> None:
        pygame.mixer.music.stop()
        self.statusBar().showMessage("已停止")

    def _on_replay(self) -> None:
        if self._current_wav and self._current_wav.is_file():
            try:
                pygame.mixer.music.rewind()
                pygame.mixer.music.play()
                self.statusBar().showMessage("正在播放")
            except Exception:
                self._on_play()
        else:
            self._on_play()

    def _on_save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存音频",
            str(self._base_dir / "pronunciation.wav"),
            "WAV (*.wav);;MP3 (*.mp3)",
        )
        if not path:
            return
        src = self._current_wav
        if src is None or not src.is_file():
            QMessageBox.information(self, "保存", "暂无可保存的音频，请先播放一次。")
            return
        dest = Path(path)
        try:
            ext = dest.suffix.lower().lstrip(".")
            fmt = ext if ext in ("wav", "mp3") else "wav"
            export_copy(src, dest, format_hint=fmt)
            self.statusBar().showMessage(f"已保存：{dest}")
        except AudioProcessingError as e:
            QMessageBox.warning(self, "保存失败", str(e))
        except Exception as e:
            QMessageBox.warning(self, "保存失败", str(e))

    def _on_syllable(self, index: int) -> None:
        prepared = self._prepared
        if prepared is None or index < 0 or index >= len(prepared.syllables):
            return
        syl = prepared.syllables[index]
        self._run_synthesis(syl, syllable=syl)
