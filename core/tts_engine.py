"""Edge-TTS synthesis for Mandarin."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import edge_tts

VOICES: dict[str, str] = {
    "female": "zh-CN-XiaoxiaoNeural",
    "male": "zh-CN-YunxiNeural",
}


class TTSError(RuntimeError):
    """Raised when synthesis fails."""


def _resolve_voice(voice_key: str) -> str:
    if voice_key not in VOICES:
        known = ", ".join(sorted(VOICES))
        raise TTSError(f"未知发音人：{voice_key!r}。可选：{known}")
    return VOICES[voice_key]


async def generate_tts_async(
    text: str,
    *,
    voice_key: str = "female",
    out_dir: Path,
    suffix: str = ".mp3",
) -> Path:
    """
    Generate speech with Microsoft Edge TTS and write to a unique file under ``out_dir``.
    """
    stripped = (text or "").strip()
    if not stripped:
        raise TTSError("合成文本为空。")

    voice = _resolve_voice(voice_key)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"tts_{uuid.uuid4().hex}{suffix}"

    try:
        communicate = edge_tts.Communicate(stripped, voice=voice)
        await communicate.save(str(out_path))
    except TTSError:
        raise
    except Exception as e:
        raise TTSError(f"语音合成失败：{e}") from e

    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise TTSError("语音合成未生成有效音频文件。")

    return out_path


def generate_tts(
    text: str,
    *,
    voice_key: str = "female",
    out_dir: Path,
    suffix: str = ".mp3",
) -> Path:
    """Synchronous wrapper for use from threads without an existing event loop."""
    return asyncio.run(
        generate_tts_async(text, voice_key=voice_key, out_dir=out_dir, suffix=suffix)
    )
