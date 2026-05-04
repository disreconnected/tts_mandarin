# Chinese Pronunciation Trainer

Desktop app for practicing Mandarin pronunciation and tones. Enter **Hanzi** or **Pinyin** (tone marks or tone numbers), hear high-quality **zh-CN** speech via Microsoft Edge TTS, adjust **tempo** without changing pitch (ffmpeg), and review **tone-colored** syllables.

## Features (Phase 1)

- **Dual input**: Chinese characters, Pinyin with tone marks (e.g. `nǐ hǎo`), or numbered Pinyin (`ni3 hao3`), with optional **Auto / 汉字 / 拼音** mode.
- **TTS**: `edge-tts` with Mandarin neural voices (**Female**: `zh-CN-XiaoxiaoNeural`, **Male**: `zh-CN-YunxiNeural`).
- **Speed**: 0.25×–2× using ffmpeg `atempo` (pitch-preserving).
- **Tone view**: Syllables with tone-colored labels (1 red, 2 green, 3 blue, 4 purple, neutral gray).
- **Playback**: Play / Pause / Stop, replay, play individual syllables, save **WAV/MP3**.

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

- **Phase 1 (current):** Mandarin TTS trainer (this app).
- **Phase 2:** English TTS with IPA-style breakdown.
- **Phase 3:** Long-text / audiobook mode with sentence splitting.
- **Phase 4:** Record user audio and compare to reference.
- **Phase 5:** Web version (e.g. FastAPI + React).

See [ROADMAP.md](ROADMAP.md) for later-phase detail.

## License

Use and modify for learning purposes; respect Microsoft Edge TTS terms of use for `edge-tts`.
