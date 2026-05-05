# Chinese Pronunciation Trainer

Desktop app for practicing Mandarin pronunciation and tones. Enter **Hanzi** or **Pinyin** (tone marks or tone numbers), hear high-quality **zh-CN** speech via Microsoft Edge TTS, adjust **tempo** without changing pitch (ffmpeg), and review **tone-colored** syllables.

## Project progress

**Overall completion: 20%** — one of five roadmap phases is shipped; each phase counts equally toward 100%.

| Phase | Scope | Status |
|------:|-------|--------|
| 1 | Mandarin desktop trainer (this repo) | **Complete (100%)** |
| 2 | English TTS and phonetics | Not started (0%) |
| 3 | Long-text / audiobook mode | Not started (0%) |
| 4 | User recording and comparison | Not started (0%) |
| 5 | Web version | Not started (0%) |

Detailed milestones, per-phase progress, and implementation notes: [ROADMAP.md](ROADMAP.md).

## Features (Phase 1)

- **Dual input**: Chinese characters, Pinyin with tone marks (e.g. `nǐ hǎo`), or numbered Pinyin (`ni3 hao3`), with optional **Auto / 汉字 / 拼音** mode.
- **TTS**: `edge-tts` with Mandarin neural voices (**Female**: `zh-CN-XiaoxiaoNeural`, **Male**: `zh-CN-YunxiNeural`).
- **Speed**: 0.25×–2× using ffmpeg `atempo` (pitch-preserving).
- **Tone view**: Syllables with tone-colored labels (1 red, 2 green, 3 blue, 4 purple, neutral gray).
- **Playback**: Play / Pause / Stop, replay, play individual syllables, save **WAV/MP3**.
- **Interface language**: **Language** menu — **English** (default) or **中文 (Simplified)**; choice is remembered.

> **Note:** Edge `zh-CN` voices are tuned for **Hanzi**. Pinyin-only sentences may sound less natural than the same phrase written in characters.

## Tech stack

- Python 3.10+
- PyQt6, pygame (audio playback)
- edge-tts, pypinyin, pydub (+ ffmpeg CLI)

## Installation

1. Clone the repository and create a virtual environment (recommended).

2. Install **ffmpeg** and ensure `ffmpeg` is on your `PATH`. See [setup_ffmpeg.md](setup_ffmpeg.md).

3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Usage

From the project root:

```bash
python main.py
```

Enter text in the left panel, choose **发音人** (Female/Male) and **语速**, then click **播放**. Click a syllable in the list to hear it alone. Use **另存为…** after a successful synthesis.

## Roadmap (high level)

- **Phase 1:** Mandarin TTS trainer — **done** (see above).
- **Phase 2:** English TTS with IPA-style breakdown.
- **Phase 3:** Long-text / audiobook mode with sentence splitting.
- **Phase 4:** Record user voice and compare with reference pronunciation.
- **Phase 5:** Web version (e.g. FastAPI + React).

See [ROADMAP.md](ROADMAP.md) for per-phase progress and recommendations.

## License

Use and modify for learning purposes; respect Microsoft Edge TTS terms of use for `edge-tts`.
