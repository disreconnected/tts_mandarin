"""Patch torch._numpy._ufuncs for PyInstaller (NameError: name 'name' is not defined).

Run before PyInstaller when building the Kokoro edition. Creates a .bak backup on first run.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def _patch_text(text: str) -> str:
    if "ufunc_name = name" in text:
        return text
    text = text.replace(
        "    vars()[name] = deco_binary_ufunc(ufunc)",
        "    ufunc_name = name\n    vars()[ufunc_name] = deco_binary_ufunc(ufunc)",
    )
    text = text.replace(
        "    vars()[name] = deco_unary_ufunc(ufunc)",
        "    ufunc_name = name\n    vars()[ufunc_name] = deco_unary_ufunc(ufunc)",
    )
    return text


def main() -> int:
    import torch._numpy._ufuncs as mod

    path = Path(mod.__file__)
    backup = path.with_suffix(path.suffix + ".tts_mandarin.bak")
    if not backup.is_file():
        shutil.copy2(path, backup)
        print(f"backup: {backup}")
    text = _patch_text(path.read_text(encoding="utf-8"))
    path.write_text(text, encoding="utf-8")
    print(f"patched: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
