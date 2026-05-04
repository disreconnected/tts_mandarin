"""Background synthesis: Edge-TTS + ffmpeg tempo in a Qt worker thread."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from core.audio_processor import apply_speed
from core.tts_engine import generate_tts


class TTSWorker(QObject):
    """
    ``finished`` carries WAV path, source MP3 path, and whether to refresh phrase cache.
    """

    finished = pyqtSignal(str, str, bool)
    failed = pyqtSignal(str)

    def __init__(self, out_dir: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._out_dir = out_dir

    @pyqtSlot(str, str, float, str, bool)
    def synthesize(
        self,
        tts_text: str,
        voice_key: str,
        speed: float,
        reuse_mp3_path: str,
        update_cache_on_success: bool,
    ) -> None:
        try:
            mp3: Path
            if reuse_mp3_path:
                mp3 = Path(reuse_mp3_path)
                if not mp3.is_file():
                    raise FileNotFoundError(f"缓存的音频已失效：{mp3}")
            else:
                mp3 = generate_tts(
                    tts_text, voice_key=voice_key, out_dir=self._out_dir
                )
            wav = apply_speed(
                mp3, speed_factor=speed, out_dir=self._out_dir, out_format="wav"
            )
            self.finished.emit(
                str(wav.resolve()),
                str(mp3.resolve()),
                update_cache_on_success,
            )
        except Exception as e:
            self.failed.emit(str(e))
