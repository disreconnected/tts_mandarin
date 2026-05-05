"""Pinyin → Hanzi for display: phrase segmentation (simplified) + per-char TTS hints."""

from __future__ import annotations

import math

from pypinyin import Style, lazy_pinyin
from pypinyin.style._tone_convert import tone_to_tone3

try:
    import wordfreq
except ImportError:  # pragma: no cover
    wordfreq = None

try:
    import zhconv
except ImportError:  # pragma: no cover
    zhconv = None

# Wordlist slice for phrase lexicon (descending frequency order).
_MAX_LEX_WORDS = 40_000
_MAX_PHRASE_SYLLABLES = 8
_NEG = -1e300

_PHRASE_LEX: dict[tuple[str, ...], tuple[str, float]] | None = None
_SINGLE_CHAR: dict[str, str] | None = None


def _simp(s: str) -> str:
    if not s or zhconv is None:
        return s
    return zhconv.convert(s, "zh-cn")


def to_simplified(s: str) -> str:
    """Convert a string to Simplified Chinese (no-op if zhconv is missing)."""
    return _simp(s)


def _syllable_to_tone3_key(syl: str) -> str:
    s = syl.strip()
    if not s:
        return ""
    s_lower = s.lower()
    if len(s_lower) >= 2 and s_lower[-1] in "12345":
        return s_lower[:-1].replace("ü", "v") + s_lower[-1]
    t3 = tone_to_tone3(s, neutral_tone_with_five=True, v_to_u=False)
    return str(t3).lower().replace("ü", "v")


def _is_hanzi_word(w: str) -> bool:
    return bool(w) and all("\u4e00" <= c <= "\u9fff" for c in w)


def _ensure_phrase_lex() -> dict[tuple[str, ...], tuple[str, float]]:
    global _PHRASE_LEX
    if _PHRASE_LEX is not None:
        return _PHRASE_LEX
    if wordfreq is None:
        _PHRASE_LEX = {}
        return _PHRASE_LEX

    lex: dict[tuple[str, ...], tuple[str, float]] = {}
    for idx, w in enumerate(wordfreq.iter_wordlist("zh", wordlist="best")):
        if idx >= _MAX_LEX_WORDS:
            break
        if not _is_hanzi_word(w):
            continue
        if len(w) > _MAX_PHRASE_SYLLABLES:
            continue
        arr = lazy_pinyin(w, style=Style.TONE3, neutral_tone_with_five=True)
        if not arr or len(arr) != len(w):
            continue
        tup = tuple(x.lower().replace("ü", "v") for x in arr)
        fq = wordfreq.word_frequency(w, "zh") or 1e-20
        prev = lex.get(tup)
        if prev is None or fq > prev[1]:
            lex[tup] = (_simp(w), fq)

    _PHRASE_LEX = lex
    return _PHRASE_LEX


def _ensure_single_char() -> dict[str, str]:
    global _SINGLE_CHAR
    if _SINGLE_CHAR is not None:
        return _SINGLE_CHAR
    if wordfreq is None:
        _SINGLE_CHAR = {}
        return _SINGLE_CHAR

    best: dict[str, tuple[str, float]] = {}
    for code in range(0x4E00, 0x9FFF + 1):
        ch = chr(code)
        chs = _simp(ch)
        arr = lazy_pinyin(chs, style=Style.TONE3, neutral_tone_with_five=True)
        if not arr or not arr[0]:
            continue
        key = arr[0].lower().replace("ü", "v")
        fq = wordfreq.word_frequency(chs, "zh") or 1e-18
        old = best.get(key)
        if old is None or fq > old[1]:
            best[key] = (chs, fq)

    _SINGLE_CHAR = {k: v[0] for k, v in best.items()}
    return _SINGLE_CHAR


def _decode_with_dp(keys: list[str]) -> list[str] | None:
    n = len(keys)
    if n == 0 or any(not k for k in keys):
        return None

    lex = _ensure_phrase_lex()
    scm = _ensure_single_char()

    dp = [_NEG] * (n + 1)
    back = [-1] * (n + 1)
    word_at: list[str | None] = [None] * (n + 1)
    dp[0] = 0.0

    for i in range(n + 1):
        if dp[i] <= _NEG / 2:
            continue
        max_l = min(_MAX_PHRASE_SYLLABLES, n - i)
        for L in range(1, max_l + 1):
            j = i + L
            tup = tuple(keys[i:j])
            w: str | None = None
            fq = 0.0
            if tup in lex:
                w, fq = lex[tup]
            elif L == 1 and tup[0] in scm:
                w = scm[tup[0]]
                fq = wordfreq.word_frequency(w, "zh") or 1e-15  # type: ignore[union-attr]
                fq *= 0.85
            if w is None:
                continue
            sc = dp[i] + math.log(fq)
            if sc > dp[j]:
                dp[j] = sc
                back[j] = i
                word_at[j] = w

    if dp[n] <= _NEG / 2:
        return None

    chunks: list[tuple[int, int, str]] = []
    pos = n
    while pos > 0:
        prev = back[pos]
        w = word_at[pos]
        if prev < 0 or w is None:
            return None
        chunks.append((prev, pos, w))
        pos = prev
    chunks.reverse()

    flat = [""] * n
    for a, b, w in chunks:
        chars = list(w)
        span = b - a
        if len(chars) == span:
            for k, ch in zip(range(a, b), chars):
                flat[k] = ch
        elif len(chars) < span:
            for k in range(len(chars)):
                flat[a + k] = chars[k]
        else:
            for k in range(span):
                flat[a + k] = chars[k]
    return flat


def guess_chars_for_syllables(syllables: list[str]) -> tuple[str, ...]:
    """
    Map each syllable to one simplified Hanzi using phrase-aware decoding.
    Falls back to single-syllable lexicon if DP cannot cover the sequence.
    """
    if not syllables:
        return ()
    keys = [_syllable_to_tone3_key(s) for s in syllables]
    if any(not k for k in keys):
        return tuple("" for _ in syllables)

    decoded = _decode_with_dp(keys)
    if decoded is not None:
        return tuple(decoded)

    scm = _ensure_single_char()
    return tuple(scm.get(k, "") for k in keys)
