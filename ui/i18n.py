"""UI copy and localized error messages (English default, optional 简体中文)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.audio_processor import AudioProcessingError
from core.input_detector import InputDetectionError
from core.tts_engine import TTSError


class UiLanguage(str, Enum):
    EN = "en"
    ZH = "zh"


@dataclass(frozen=True)
class UiTexts:
    window_title: str
    menu_language: str
    lang_english: str
    lang_chinese: str
    # Input panel
    group_input: str
    label_detection_mode: str
    mode_auto: str
    mode_hanzi: str
    mode_pinyin: str
    placeholder_input: str
    # Playback
    group_playback: str
    label_speed: str
    label_voice: str
    voice_female: str
    voice_male: str
    btn_play: str
    btn_pause: str
    btn_stop: str
    btn_replay: str
    btn_save: str
    label_syllables: str
    # Status
    status_ready: str
    status_synthesizing: str
    status_playing: str
    status_paused: str
    status_stopped: str
    status_saved: str
    # Dialogs
    dlg_invalid_input: str
    dlg_error: str
    dlg_playback_failed: str
    dlg_synthesis_failed: str
    dlg_save_audio: str
    dlg_save: str
    dlg_save_nothing: str
    dlg_save_failed: str


def texts(lang: UiLanguage) -> UiTexts:
    if lang == UiLanguage.ZH:
        return UiTexts(
            window_title="汉语发音练习器",
            menu_language="界面语言 (&L)",
            lang_english="English",
            lang_chinese="中文（简体）",
            group_input="输入",
            label_detection_mode="识别方式：",
            mode_auto="自动检测",
            mode_hanzi="汉字模式",
            mode_pinyin="拼音模式",
            placeholder_input="输入汉字（你好）或拼音（nǐ hǎo / ni3 hao3）…",
            group_playback="播放",
            label_speed="语速：",
            label_voice="发音人：",
            voice_female="女声",
            voice_male="男声",
            btn_play="播放",
            btn_pause="暂停",
            btn_stop="停止",
            btn_replay="重播",
            btn_save="另存为…",
            label_syllables="单字 / 音节：",
            status_ready="就绪",
            status_synthesizing="正在合成语音…",
            status_playing="正在播放",
            status_paused="已暂停",
            status_stopped="已停止",
            status_saved="已保存：{path}",
            dlg_invalid_input="输入无效",
            dlg_error="错误",
            dlg_playback_failed="播放失败",
            dlg_synthesis_failed="合成失败",
            dlg_save_audio="保存音频",
            dlg_save="保存",
            dlg_save_nothing="暂无可保存的音频，请先播放一次。",
            dlg_save_failed="保存失败",
        )
    return UiTexts(
        window_title="Chinese Pronunciation Trainer",
        menu_language="&Language",
        lang_english="English",
        lang_chinese="中文 (Simplified)",
        group_input="Input",
        label_detection_mode="Detection:",
        mode_auto="Auto-detect",
        mode_hanzi="Chinese characters",
        mode_pinyin="Pinyin",
        placeholder_input="Enter Hanzi (你好) or Pinyin (nǐ hǎo / ni3 hao3)…",
        group_playback="Playback",
        label_speed="Speed:",
        label_voice="Voice:",
        voice_female="🎙️ Female",
        voice_male="🎙️ Male",
        btn_play="Play",
        btn_pause="Pause",
        btn_stop="Stop",
        btn_replay="Replay",
        btn_save="Save as…",
        label_syllables="Syllables:",
        status_ready="Ready",
        status_synthesizing="Synthesizing speech…",
        status_playing="Playing",
        status_paused="Paused",
        status_stopped="Stopped",
        status_saved="Saved: {path}",
        dlg_invalid_input="Invalid input",
        dlg_error="Error",
        dlg_playback_failed="Playback failed",
        dlg_synthesis_failed="Synthesis failed",
        dlg_save_audio="Save audio",
        dlg_save="Save",
        dlg_save_nothing="Nothing to save yet. Play audio once first.",
        dlg_save_failed="Save failed",
    )


def format_input_error(lang: UiLanguage, err: InputDetectionError) -> str:
    key = err.key
    if lang == UiLanguage.ZH:
        zh = {
            "empty_input": "请输入文字或拼音。",
            "unrecognized_input": "无法识别输入：请使用汉字、带声调拼音或数字声调拼音（如 ni3 hao3）。",
            "hanzi_mode_needs_cjk": "当前为「汉字」模式：请输入包含汉字的文本。",
            "pinyin_empty": "请输入拼音。",
            "pinyin_invalid_tokens": "拼音模式：请使用带声调或数字声调的拼音，音节之间用空格分隔。",
        }
        return zh.get(key, key)
    en = {
        "empty_input": "Please enter text or pinyin.",
        "unrecognized_input": "Could not parse input. Use Hanzi, tone-marked Pinyin, or numbered Pinyin (e.g. ni3 hao3).",
        "hanzi_mode_needs_cjk": "Chinese-character mode requires at least one Chinese character.",
        "pinyin_empty": "Please enter pinyin.",
        "pinyin_invalid_tokens": "Pinyin mode: use letters and tones (1–5) or tone marks; separate syllables with spaces.",
    }
    return en.get(key, key)


def format_tts_error(lang: UiLanguage, err: TTSError) -> str:
    k = err.key
    p = err.params
    if lang == UiLanguage.ZH:
        zh = {
            "unknown_voice": "未知发音人：{voice!r}。可选：{known}",
            "empty_tts_text": "合成文本为空。",
            "synth_failed": "语音合成失败：{detail}",
            "no_audio_output": "语音合成未生成有效音频文件。",
        }
        return zh[k].format(**p)
    en = {
        "unknown_voice": "Unknown voice: {voice!r}. Options: {known}",
        "empty_tts_text": "Nothing to synthesize (empty text).",
        "synth_failed": "Speech synthesis failed: {detail}",
        "no_audio_output": "Synthesis did not produce a valid audio file.",
    }
    return en[k].format(**p)


def format_audio_error(lang: UiLanguage, err: AudioProcessingError) -> str:
    k = err.key
    p = {**err.params}
    p.setdefault("doc", "setup_ffmpeg.md")
    if lang == UiLanguage.ZH:
        zh = {
            "ffmpeg_missing": "未找到 ffmpeg。请安装 ffmpeg 并加入 PATH，参见 {doc}。",
            "speed_invalid": "播放速度必须大于 0。",
            "input_missing": "找不到输入音频：{path}",
            "ffmpeg_exec_failed": "无法启动 ffmpeg。请安装并配置 PATH，参见 {doc}。",
            "ffmpeg_failed": "ffmpeg 处理失败：{detail}",
            "no_output_file": "ffmpeg 未生成输出文件。",
        }
        return zh[k].format(**p)
    en = {
        "ffmpeg_missing": "ffmpeg not found. Install ffmpeg and add it to PATH (see {doc}).",
        "speed_invalid": "Playback speed must be greater than zero.",
        "input_missing": "Input audio not found: {path}",
        "ffmpeg_exec_failed": "Could not run ffmpeg. Install it and ensure PATH is set (see {doc}).",
        "ffmpeg_failed": "ffmpeg error: {detail}",
        "no_output_file": "ffmpeg did not produce an output file.",
    }
    return en[k].format(**p)


def format_worker_failure(lang: UiLanguage, exc: BaseException) -> str:
    if isinstance(exc, TTSError):
        return format_tts_error(lang, exc)
    if isinstance(exc, AudioProcessingError):
        return format_audio_error(lang, exc)
    if lang == UiLanguage.ZH:
        return f"意外错误：{exc}"
    return f"Unexpected error: {exc}"
