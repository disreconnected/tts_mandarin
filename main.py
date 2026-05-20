"""Entry point for Chinese Pronunciation Trainer."""

from __future__ import annotations

import sys
from pathlib import Path

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
