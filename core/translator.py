"""Simple translation helpers backed by deep-translator (GoogleTranslator)."""

from __future__ import annotations

from dataclasses import dataclass

from deep_translator import GoogleTranslator


@dataclass(frozen=True)
class TranslationError(RuntimeError):
    """Raised when translation input is invalid or translation fails."""

    key: str
    detail: str = ""

    def __str__(self) -> str:
        if self.detail:
            return f"{self.key}: {self.detail}"
        return self.key


def translate_text(text: str, source: str = "auto", target: str = "zh-CN") -> str:
    """Translate ``text`` using GoogleTranslator with simple validation/errors."""
    stripped = text.strip()
    if not stripped:
        raise TranslationError("empty_input")
    try:
        out = GoogleTranslator(source=source, target=target).translate(stripped)
    except Exception as e:  # network/provider/format errors
        raise TranslationError("translate_failed", str(e)) from e
    if not out or not str(out).strip():
        raise TranslationError("empty_result")
    return str(out).strip()
