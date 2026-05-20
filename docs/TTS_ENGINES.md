# TTS engines and voices

The app supports two synthesis backends. Choose **TTS engine** in the Playback panel.

## 1. Microsoft Edge (default)

- **Online** — uses `edge-tts` (same neural voices as the Edge browser).
- **Voices:** female `zh-CN-XiaoxiaoNeural`, male `zh-CN-YunxiNeural` (keys `female` / `male` in code).
- **Best for:** no large local install; familiar teacher-style pace (Edge rate tuned in `core/tts_engine.py`).

## 2. Kokoro (local)

- **Local inference** — [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) via the `kokoro` Python package (`KPipeline`, `lang_code='z'` for Mandarin).
- **Offline-capable** after models are downloaded on first use.
- **Dependencies:** see `requirements.txt` (`kokoro`, `soundfile`, `misaki[zh]`, pulls `torch`, etc.).
- **Windows:** installing [espeak-ng](https://github.com/espeak-ng/espeak-ng/releases) is recommended for robust G2P fallback (upstream Kokoro README).

This build exposes **four** Mandarin voices (see `core/kokoro_tts_engine.py`):

| Voice ID | English UI label | 中文 |
|----------|------------------|------|
| `zf_xiaoyi` | Xiaoyi (female) | 小艺（女） |
| `zf_xiaobei` | Xiaobei (female) | 小贝（女） |
| `zm_yunjian` | Yunjian (male) | 云健（男） |
| `zm_yunxia` | Yunxia (male) | 云夏（男） |

Default voice: **`zf_xiaoyi`**.

The full upstream catalog (8 Mandarin voices) is in [Kokoro VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md); this app only ships the four above.

## Frozen **Kokoro** Windows build

To produce **`ChinesePronunciationTrainerKokoro`** (folder next to `dist\`), use the script and notes in [BUILD_WINDOWS.md](BUILD_WINDOWS.md) (Kokoro edition section).
