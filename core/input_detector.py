"""Detect whether user input is Hanzi, tone-marked Pinyin, or numbered Pinyin."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class InputKind(Enum):
    HANZI = auto()
    MARKED_PINYIN = auto()
    NUMBERED_PINYIN = auto()


# CJK Unified Ideographs + common extensions used in modern Chinese text
_HANZI_RE = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]"
)

# Precomposed / common Latin letters with tone marks used in Pinyin
_MARKED_VOWEL_RE = re.compile(
    r"[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛÜ]"
)

_NUMBERED_TOKEN_RE = re.compile(r"^[a-zA-ZüÜ]+[1-5]?$", re.IGNORECASE)

_MARKED_PINYIN_TOKEN_RE = re.compile(
    r"^[a-zA-ZüÜāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜńňḿ"
    r"ĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛÜŃŇḾ'\-]+$"
)


@dataclass(frozen=True)
class InputDetection:
    kind: InputKind
    text: str


class InputDetectionError(ValueError):
    """Raised when input is empty or cannot be classified (``key`` for UI translation)."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(key)


def _strip_and_validate(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        raise InputDetectionError("empty_input")
    return cleaned


def detect_input(text: str, *, force_kind: InputKind | None = None) -> InputDetection:
    """
    Classify trimmed input. When ``force_kind`` is set, skip heuristics and trust it
    (still rejects empty input).
    """
    cleaned = _strip_and_validate(text)
    if force_kind is not None:
        return InputDetection(force_kind, cleaned)

    if _HANZI_RE.search(cleaned):
        return InputDetection(InputKind.HANZI, cleaned)

    if _MARKED_VOWEL_RE.search(cleaned):
        return InputDetection(InputKind.MARKED_PINYIN, cleaned)

    parts = [p for p in re.split(r"\s+", cleaned) if p]
    if parts and all(_NUMBERED_TOKEN_RE.fullmatch(p) for p in parts):
        if any(p[-1].isdigit() for p in parts):
            return InputDetection(InputKind.NUMBERED_PINYIN, cleaned)

    # Plain ASCII pinyin without digits or tone marks → treat as marked/neutral
    if re.fullmatch(r"[a-zA-ZüÜ\s\.\-']+", cleaned, re.IGNORECASE):
        return InputDetection(InputKind.MARKED_PINYIN, cleaned)

    raise InputDetectionError("unrecognized_input")


def detect_hanzi_only(text: str) -> InputDetection:
    """Treat input as Hanzi; reject if there are no CJK characters."""
    cleaned = _strip_and_validate(text)
    if not _HANZI_RE.search(cleaned):
        raise InputDetectionError("hanzi_mode_needs_cjk")
    return InputDetection(InputKind.HANZI, cleaned)


def detect_pinyin_only(text: str) -> InputDetection:
    """Skip Hanzi detection; classify as numbered or marked Pinyin."""
    cleaned = _strip_and_validate(text)
    parts = [p for p in re.split(r"\s+", cleaned) if p]
    if not parts:
        raise InputDetectionError("pinyin_empty")

    if all(_NUMBERED_TOKEN_RE.fullmatch(p) for p in parts):
        if any(p[-1].isdigit() for p in parts):
            return InputDetection(InputKind.NUMBERED_PINYIN, cleaned)
        return InputDetection(InputKind.MARKED_PINYIN, cleaned)

    if all(_MARKED_PINYIN_TOKEN_RE.fullmatch(p) for p in parts):
        return InputDetection(InputKind.MARKED_PINYIN, cleaned)

    raise InputDetectionError("pinyin_invalid_tokens")
