"""Hanzi → Pinyin and numbered Pinyin → tone-marked syllables for display and TTS."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pypinyin import Style, lazy_pinyin
from pypinyin.style._tone_convert import tone3_to_tone

from core.input_detector import InputDetection, InputKind


_TONE_MARK_CHARS = set("āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüńňḿĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛÜŃŇ")


def _split_pinyin_tokens(text: str) -> list[str]:
    return [t for t in re.split(r"\s+", text.strip()) if t]


def numbered_to_marked(text: str) -> list[str]:
    """Convert whitespace-separated numbered syllables to tone-marked forms."""
    out: list[str] = []
    for raw in _split_pinyin_tokens(text):
        m = re.fullmatch(r"([a-zA-ZüÜ]+)([1-5]?)", raw, re.IGNORECASE)
        if not m:
            out.append(raw)
            continue
        body, num = m.group(1), m.group(2)
        if not num:
            out.append(body.lower())
            continue
        try:
            out.append(tone3_to_tone(f"{body.lower()}{num}"))
        except Exception:
            out.append(raw)
    return out


def marked_syllables_from_text(text: str) -> list[str]:
    """Split tone-marked or plain ASCII pinyin into syllables."""
    return _split_pinyin_tokens(text)


@dataclass(frozen=True)
class PreparedPhrase:
    """Text for Edge-TTS and syllables for UI / per-syllable playback."""

    tts_text: str
    syllables: list[str]
    syllable_tones: list[int]
    source_kind: InputKind


def _tone_from_syllable(syl: str) -> int:
    """Return tone 1–4, 5 for neutral/light, 0 if unknown."""
    if re.search(r"[1-5]$", syl):
        return int(syl[-1])
    for ch in syl:
        if ch in "āēīōūǖĀĒĪŌŪǕ":
            return 1
        if ch in "áéíóúǘÁÉÍÓÚǗ":
            return 2
        if ch in "ǎěǐǒǔǚǍĚǏǑǓǙ":
            return 3
        if ch in "àèìòùǜÀÈÌÒÙǛ":
            return 4
        if ch in "ńňḿŃŇḾ":
            return 5
    if "ü" in syl.lower() and not any(c in _TONE_MARK_CHARS for c in syl):
        return 5
    return 5


def prepare_phrase(detection: InputDetection) -> PreparedPhrase:
    """
    Build TTS string and parallel syllable list.

    Hanzi: TTS uses original characters; syllables come from pypinyin TONE style.
    Pinyin: TTS uses space-joined tone-marked syllables (quality may vary vs Hanzi).
    """
    kind = detection.kind
    text = detection.text

    if kind == InputKind.HANZI:
        syllables = lazy_pinyin(text, style=Style.TONE, neutral_tone_with_five=True)
        tts_text = text
        tones = [_tone_from_syllable(s) for s in syllables]
        return PreparedPhrase(
            tts_text=tts_text,
            syllables=syllables,
            syllable_tones=tones,
            source_kind=kind,
        )

    if kind == InputKind.NUMBERED_PINYIN:
        syllables = numbered_to_marked(text)
        tts_text = " ".join(syllables)
        tones = [_tone_from_syllable(s) for s in syllables]
        return PreparedPhrase(
            tts_text=tts_text,
            syllables=syllables,
            syllable_tones=tones,
            source_kind=kind,
        )

    # MARKED_PINYIN or plain ASCII
    syllables = marked_syllables_from_text(text)
    tts_text = " ".join(syllables)
    tones = [_tone_from_syllable(s) for s in syllables]
    return PreparedPhrase(
        tts_text=tts_text,
        syllables=syllables,
        syllable_tones=tones,
        source_kind=kind,
    )
