"""Entry point for Chinese Pronunciation Trainer."""

from __future__ import annotations

import os
import sys
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


def main() -> None:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent
    app = QApplication(sys.argv)
    win = MainWindow(base_dir)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
