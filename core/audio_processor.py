"""Load synthesized audio and apply pitch-preserving tempo with ffmpeg atempo."""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from pydub import AudioSegment
from pydub.utils import which

SETUP_DOC = "setup_ffmpeg.md"


class AudioProcessingError(RuntimeError):
    """Raised when ffmpeg/pydub processing fails."""


def _ensure_ffmpeg() -> None:
    if not which("ffmpeg"):
        raise AudioProcessingError(
            f"未找到 ffmpeg。请安装 ffmpeg 并加入 PATH，参见 {SETUP_DOC}。"
        )


def _atempo_filter_chain(speed_factor: float) -> str | None:
    """Return ffmpeg atempo chain for ``speed_factor`` (0.25–2.0 supported)."""
    if speed_factor <= 0:
        raise AudioProcessingError("播放速度必须大于 0。")
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
    _ensure_ffmpeg()
    if not input_path.is_file():
        raise AudioProcessingError(f"找不到输入音频：{input_path}")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"proc_{uuid.uuid4().hex}.{out_format}"

    chain = _atempo_filter_chain(speed_factor)
    if chain is None:
        # No tempo change: still normalize to WAV for pygame via pydub
        audio = AudioSegment.from_file(str(input_path))
        audio.export(str(out_path), format=out_format)
        return out_path

    cmd = [
        "ffmpeg",
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
        raise AudioProcessingError(
            f"无法启动 ffmpeg。请安装并配置 PATH，参见 {SETUP_DOC}。"
        ) from e
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or "").strip() or str(e)
        raise AudioProcessingError(f"ffmpeg 处理失败：{msg}") from e

    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise AudioProcessingError("ffmpeg 未生成输出文件。")

    return out_path


def export_copy(input_path: Path, dest_path: Path, format_hint: str | None = None) -> None:
    """Export audio to ``dest_path`` (extension decides format)."""
    _ensure_ffmpeg()
    fmt = format_hint
    if fmt is None:
        ext = dest_path.suffix.lower().lstrip(".")
        fmt = ext if ext else "wav"
    audio = AudioSegment.from_file(str(input_path))
    audio.export(str(dest_path), format=fmt)
