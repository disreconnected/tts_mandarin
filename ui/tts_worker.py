"""Background synthesis: Edge or Kokoro TTS + ffmpeg tempo in a Qt worker thread."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from core.audio_processor import AudioProcessingError, apply_speed
from core.kokoro_tts_engine import generate_kokoro_tts
from core.tts_engine import TTSError, generate_tts
from ui.i18n import UiLanguage, format_worker_failure


class TTSWorker(QObject):
    """
    ``finished`` carries the final WAV path, the pre-tempo source audio path (MP3 or WAV),
    and whether to refresh the phrase cache.
    ``failed`` emits a user-facing error string.
    """

    finished = pyqtSignal(str, str, bool)
    failed = pyqtSignal(str)

    def __init__(self, out_dir: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._out_dir = out_dir

    @pyqtSlot(str, str, str, float, str, bool, str)
    def synthesize(
        self,
        tts_text: str,
        engine: str,
        voice_key: str,
        speed: float,
        reuse_src_path: str,
        update_cache_on_success: bool,
        ui_lang_code: str,
    ) -> None:
        try:
            lang = UiLanguage(ui_lang_code)
        except ValueError:
            lang = UiLanguage.EN
        try:
            src: Path
            if reuse_src_path:
                src = Path(reuse_src_path)
                if not src.is_file():
                    raise FileNotFoundError(str(src))
            elif engine == "kokoro":
                src = generate_kokoro_tts(
                    tts_text, voice_key=voice_key, out_dir=self._out_dir
                )
            else:
                src = generate_tts(
                    tts_text, voice_key=voice_key, out_dir=self._out_dir
                )
            wav = apply_speed(
                src, speed_factor=speed, out_dir=self._out_dir, out_format="wav"
            )
            self.finished.emit(
                str(wav.resolve()),
                str(src.resolve()),
                update_cache_on_success,
            )
        except (TTSError, AudioProcessingError) as e:
            self.failed.emit(format_worker_failure(lang, e))
        except FileNotFoundError as e:
            if lang == UiLanguage.ZH:
                self.failed.emit(f"缓存的音频已失效：{e}")
            else:
                self.failed.emit(f"Cached audio file is missing: {e}")
        except Exception as e:
            self.failed.emit(format_worker_failure(lang, e))
