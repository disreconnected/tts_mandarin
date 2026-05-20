"""Kokoro-82M local TTS (hexgrad/kokoro) for Mandarin Chinese.

Uses ``KPipeline(lang_code='z')`` with legacy ``ZHG2P`` (jieba + pypinyin) for
reliable frozen builds. Curated Mandarin voices only.

Requires: ``pip install kokoro soundfile misaki[zh]`` (see ``requirements.txt``).
"""

from __future__ import annotations

import os
import sys
import traceback
import uuid
from pathlib import Path
from typing import Final

import numpy as np
import soundfile as sf

from core.tts_engine import TTSError

KOKORO_REPO_ID = "hexgrad/Kokoro-82M"

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


def _ensure_stdio() -> None:
    """Kokoro configures loguru with ``sys.stderr``; windowed PyInstaller exe has None."""
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")


def _configure_hf_cache(base_dir: Path | None) -> None:
    """Keep Hugging Face downloads next to the exe when frozen."""
    if not getattr(sys, "frozen", False) or base_dir is None:
        return
    cache = base_dir / "hf_cache"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(cache))
    os.environ.setdefault("HF_HUB_CACHE", str(cache / "hub"))


def _write_kokoro_debug(base_dir: Path | None, exc: BaseException) -> None:
    if base_dir is None:
        return
    try:
        log_dir = base_dir / "temp_audio"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "kokoro_error.log").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
    except OSError:
        pass


def _kokoro_unavailable_detail(exc: BaseException, base_dir: Path | None = None) -> str:
    if getattr(sys, "frozen", False):
        log_hint = ""
        if base_dir is not None:
            log_hint = f" Details: {base_dir / 'temp_audio' / 'kokoro_error.log'}"
        return (
            "Kokoro could not start in this app build. "
            "Try Microsoft Edge TTS, or rebuild with scripts/build_kokoro_edition.ps1. "
            f"({exc}){log_hint}"
        )
    return (
        "Kokoro TTS is not available. Install: pip install kokoro soundfile misaki[zh]. "
        f"({exc})"
    )


def _get_pipeline(base_dir: Path | None = None):
    """Lazy singleton ``KPipeline`` for zh (lang_code='z')."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    _ensure_stdio()
    _configure_hf_cache(base_dir)
    try:
        from kokoro import KPipeline
        from misaki import zh as misaki_zh

        pipe = KPipeline(lang_code="z", repo_id=KOKORO_REPO_ID)
        # Use legacy G2P (no ZHFrontend / pypinyin_dict) — fewer deps, works in PyInstaller.
        pipe.g2p = misaki_zh.ZHG2P(version=None)
        _pipeline = pipe
    except Exception as e:
        _write_kokoro_debug(base_dir, e)
        raise TTSError(
            "synth_failed",
            detail=_kokoro_unavailable_detail(e, base_dir),
        ) from e
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
    base_dir: Path | None = None,
) -> Path:
    """
    Synthesize Mandarin with Kokoro, write a 24 kHz mono WAV under ``out_dir``.

    ``base_dir`` should be the app root (exe folder when frozen) for HF cache + logs.
    """
    stripped = (text or "").strip()
    if not stripped:
        raise TTSError("empty_tts_text")

    voice = _resolve_voice(voice_key)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"kokoro_{uuid.uuid4().hex}.wav"

    pipeline = _get_pipeline(base_dir)
    chunks: list = []
    try:
        generator = pipeline(stripped, voice=voice, speed=1.0)
        for _gs, _ps, audio in generator:
            chunks.append(audio)
    except TTSError:
        raise
    except Exception as e:
        _write_kokoro_debug(base_dir, e)
        raise TTSError("synth_failed", detail=str(e)) from e

    audio_np = _chunks_to_numpy(chunks)
    try:
        sf.write(str(out_path), audio_np, 24000, subtype="PCM_16")
    except Exception as e:
        raise TTSError("synth_failed", detail=str(e)) from e

    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise TTSError("no_audio_output")

    return out_path
