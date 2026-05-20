"""Entry point for Chinese Pronunciation Trainer."""

from __future__ import annotations

import os
import sys

# PyInstaller + torch: for-loop over ``name`` in torch._numpy._ufuncs breaks unless
# dynamo is disabled before any torch/transformers import (Kokoro loads both).
os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")

from pathlib import Path


def _fix_stdio_for_windowed_frozen() -> None:
    """PyInstaller --windowed sets stdout/stderr to None; Kokoro uses loguru on stderr."""
    if not getattr(sys, "frozen", False):
        return
    devnull = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = devnull
    if sys.stdout is None:
        sys.stdout = devnull


_fix_stdio_for_windowed_frozen()

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def _kokoro_selftest(base_dir: Path) -> None:
    """Headless Kokoro check for frozen builds: set TTS_KOKORO_SELFTEST=1."""
    from core.kokoro_tts_engine import generate_kokoro_tts

    out = generate_kokoro_tts(
        "你好",
        voice_key="zf_xiaoyi",
        out_dir=base_dir / "temp_audio",
        base_dir=base_dir,
    )
    log = base_dir / "temp_audio" / "kokoro_selftest_ok.txt"
    log.write_text(str(out.resolve()), encoding="utf-8")


def main() -> None:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent
    if os.environ.get("TTS_KOKORO_SELFTEST") == "1":
        try:
            _kokoro_selftest(base_dir)
        except Exception as exc:
            err = base_dir / "temp_audio" / "kokoro_selftest_error.txt"
            err.parent.mkdir(parents=True, exist_ok=True)
            import traceback

            err.write_text(traceback.format_exc(), encoding="utf-8")
            raise SystemExit(1) from exc
        raise SystemExit(0)
    app = QApplication(sys.argv)
    win = MainWindow(base_dir)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
