"""Kokoro-82M local TTS (hexgrad/kokoro) for Mandarin Chinese.

Uses ``KPipeline(lang_code='z')`` and a curated subset of Kokoro Mandarin voices.

Requires: ``pip install kokoro soundfile misaki[zh]`` (see ``requirements.txt``).
On Windows, installing `espeak-ng`_ is recommended for robust G2P fallback.

.. _espeak-ng: https://github.com/espeak-ng/espeak-ng/releases
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Final

import numpy as np
import soundfile as sf

from core.tts_engine import TTSError

# Curated Kokoro-82M Mandarin voices shipped in this app (subset of full VOICES.md).
# Order = UI dropdown order.
# Source voice IDs: https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
KOKORO_VOICE_LABELS_EN: Final[dict[str, str]] = {
    "zf_xiaoyi": "Xiaoyi (female)",
    "zf_xiaobei": "Xiaobei (female)",
    "zm_yunjian": "Yunjian (male)",
    "zm_yunxia": "Yunxia (male)",
}

KOKORO_VOICE_LABELS_ZH: Final[dict[str, str]] = {
    "zf_xiaoyi": "小艺（女）",
    "zf_xiaobei": "小贝（女）",
    "zm_yunjian": "云健（男）",
    "zm_yunxia": "云夏（男）",
}

KOKORO_VOICE_ORDER: Final[tuple[str, ...]] = (
    "zf_xiaoyi",
    "zf_xiaobei",
    "zm_yunjian",
    "zm_yunxia",
)

DEFAULT_KOKORO_VOICE = "zf_xiaoyi"

_pipeline = None


def _get_pipeline():
    """Lazy singleton ``KPipeline`` for zh (lang_code='z')."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    try:
        from kokoro import KPipeline
    except Exception as e:
        raise TTSError(
            "synth_failed",
            detail=(
                "Kokoro TTS is not available. Install dependencies: "
                f"pip install kokoro soundfile misaki[zh]. ({e})"
            ),
        ) from e
    _pipeline = KPipeline(lang_code="z")
    return _pipeline


def list_kokoro_voices(ui_lang: str = "en") -> list[tuple[str, str]]:
    """Return (voice_id, display_label) in UI order."""
    labels = KOKORO_VOICE_LABELS_ZH if ui_lang.startswith("zh") else KOKORO_VOICE_LABELS_EN
    return [(vid, labels[vid]) for vid in KOKORO_VOICE_ORDER]


def _resolve_voice(voice_key: str) -> str:
    if voice_key in KOKORO_VOICE_LABELS_EN:
        return voice_key
    known = ", ".join(KOKORO_VOICE_ORDER)
    raise TTSError("unknown_voice", voice=voice_key, known=known)


def _chunks_to_numpy(chunks: list) -> np.ndarray:
    if not chunks:
        raise TTSError("no_audio_output")
    first = chunks[0]
    try:
        import torch

        if isinstance(first, torch.Tensor):
            parts = [c.detach().cpu().numpy() for c in chunks]
        else:
            parts = [np.asarray(c, dtype=np.float32) for c in chunks]
    except Exception:
        parts = [np.asarray(c, dtype=np.float32) for c in chunks]
    if len(parts) == 1:
        out = parts[0]
    else:
        out = np.concatenate(parts, axis=0)
    if out.size == 0:
        raise TTSError("no_audio_output")
    return np.squeeze(out).astype(np.float32, copy=False)


def generate_kokoro_tts(
    text: str,
    *,
    voice_key: str = DEFAULT_KOKORO_VOICE,
    out_dir: Path,
) -> Path:
    """
    Synthesize Mandarin with Kokoro, write a 24 kHz mono WAV under ``out_dir``.

    Playback speed is applied later via ``apply_speed`` (same as Edge TTS path).
    """
    stripped = (text or "").strip()
    if not stripped:
        raise TTSError("empty_tts_text")

    voice = _resolve_voice(voice_key)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"kokoro_{uuid.uuid4().hex}.wav"

    pipeline = _get_pipeline()
    chunks: list = []
    try:
        # speed=1.0: user-facing tempo still handled by ffmpeg atempo in the worker.
        generator = pipeline(stripped, voice=voice, speed=1.0)
        for _gs, _ps, audio in generator:
            chunks.append(audio)
    except TTSError:
        raise
    except Exception as e:
        raise TTSError("synth_failed", detail=str(e)) from e

    audio_np = _chunks_to_numpy(chunks)
    try:
        sf.write(str(out_path), audio_np, 24000, subtype="PCM_16")
    except Exception as e:
        raise TTSError("synth_failed", detail=str(e)) from e

    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise TTSError("no_audio_output")

    return out_path
