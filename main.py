"""Entry point for Chinese Pronunciation Trainer."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    app = QApplication(sys.argv)
    win = MainWindow(base_dir)
    win.resize(960, 640)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
