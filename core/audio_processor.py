"""Load synthesized audio and apply pitch-preserving tempo with ffmpeg atempo.

The ffmpeg binary is bundled via ``imageio-ffmpeg`` (a pip-installed static build),
so the app needs no system ffmpeg on PATH for either dev or PyInstaller-frozen runs.
A PATH-based ``ffmpeg`` is used as a fallback if the bundle is unavailable.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path

from pydub import AudioSegment

SETUP_DOC = "setup_ffmpeg.md"


def _bundled_ffmpeg_path() -> str | None:
    """Return path to the imageio-ffmpeg bundled binary, or ``None`` if unavailable."""
    try:
        import imageio_ffmpeg  # type: ignore
    except Exception:
        return None
    try:
        path = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None
    if path and os.path.isfile(path):
        return path
    return None


def _resolve_ffmpeg() -> str | None:
    """Prefer bundled ffmpeg (imageio-ffmpeg); fall back to PATH lookup."""
    bundled = _bundled_ffmpeg_path()
    if bundled:
        return bundled
    return shutil.which("ffmpeg")


_FFMPEG_PATH: str | None = _resolve_ffmpeg()
if _FFMPEG_PATH:
    # Make pydub use the same binary (avoids a separate PATH lookup).
    AudioSegment.converter = _FFMPEG_PATH


class AudioProcessingError(RuntimeError):
    """Raised when ffmpeg/pydub processing fails (``key`` / ``params`` for UI translation)."""

    def __init__(self, key: str, **params: object) -> None:
        self.key = key
        self.params = params
        super().__init__(key)


def _ensure_ffmpeg() -> str:
    """Return the ffmpeg binary path, re-resolving if not previously found."""
    global _FFMPEG_PATH
    if _FFMPEG_PATH and os.path.isfile(_FFMPEG_PATH):
        return _FFMPEG_PATH
    _FFMPEG_PATH = _resolve_ffmpeg()
    if _FFMPEG_PATH:
        AudioSegment.converter = _FFMPEG_PATH
        return _FFMPEG_PATH
    raise AudioProcessingError("ffmpeg_missing", doc=SETUP_DOC)


def _format_from_path(p: Path) -> str:
    """Derive a pydub ``format=`` hint from a file extension (skips ffprobe)."""
    ext = p.suffix.lower().lstrip(".")
    return ext or "wav"


def _atempo_filter_chain(speed_factor: float) -> str | None:
    """Return ffmpeg atempo chain for ``speed_factor`` (0.25–2.0 supported)."""
    if speed_factor <= 0:
        raise AudioProcessingError("speed_invalid")
    if abs(speed_factor - 1.0) < 1e-6:
        return None

    tempos: list[float] = []
    x = float(speed_factor)
    while x < 0.5 - 1e-9:
        tempos.append(0.5)
        x /= 0.5
    while x > 2.0 + 1e-9:
        tempos.append(2.0)
        x /= 2.0
    tempos.append(round(x, 4))
    return ",".join(f"atempo={t}" for t in tempos)


def apply_speed(
    input_path: Path,
    *,
    speed_factor: float,
    out_dir: Path,
    out_format: str = "wav",
) -> Path:
    """
    Write a new audio file with tempo changed by ``speed_factor`` without pitch shift
    (ffmpeg ``atempo``). Returns path to output file.
    """
    ffmpeg_exe = _ensure_ffmpeg()
    if not input_path.is_file():
        raise AudioProcessingError("input_missing", path=str(input_path))

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"proc_{uuid.uuid4().hex}.{out_format}"

    chain = _atempo_filter_chain(speed_factor)
    if chain is None:
        audio = AudioSegment.from_file(
            str(input_path), format=_format_from_path(input_path)
        )
        audio.export(str(out_path), format=out_format)
        return out_path

    cmd = [
        ffmpeg_exe,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-filter:a",
        chain,
        str(out_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise AudioProcessingError("ffmpeg_exec_failed", doc=SETUP_DOC) from e
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or "").strip() or str(e)
        raise AudioProcessingError("ffmpeg_failed", detail=msg) from e

    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise AudioProcessingError("no_output_file")

    return out_path


def export_copy(input_path: Path, dest_path: Path, format_hint: str | None = None) -> None:
    """Export audio to ``dest_path`` (extension decides format)."""
    _ensure_ffmpeg()
    fmt = format_hint
    if fmt is None:
        ext = dest_path.suffix.lower().lstrip(".")
        fmt = ext if ext else "wav"
    audio = AudioSegment.from_file(
        str(input_path), format=_format_from_path(input_path)
    )
    audio.export(str(dest_path), format=fmt)
