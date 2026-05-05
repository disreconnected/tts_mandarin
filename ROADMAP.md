# Roadmap

This file tracks **per-phase progress** (0–100% within each phase) and **share of the whole project**.

**Whole-project rule (also in [README.md](README.md)):** five phases are weighted equally — **20% of total progress per phase**. Overall completion is the sum of each phase’s completion × 20%.

| Phase | Title | Phase progress | Adds to overall |
|------:|-------|----------------:|----------------:|
| 1 | Mandarin desktop trainer | **100%** | **+20%** (overall **20%**) |
| 2 | English TTS and phonetics | 0% | +0% |
| 3 | Audiobook / long text | 0% | +0% |
| 4 | User recording and comparison | 0% | +0% |
| 5 | Web version | 0% | +0% |

*Each row’s contribution = phase progress × 20%. Example: Phase 2 at 50% → +10% overall.*

---

## Phase 1: Mandarin desktop trainer — **100%**

**Delivered:** PyQt6 app with Hanzi/Pinyin detection, `pypinyin` + tone UI, `edge-tts` (female/male zh-CN), ffmpeg `atempo` playback speed, pygame transport, temp audio cleanup, syllable replay, export WAV/MP3.

**Recommendations (maintenance):**

- Add automated tests for `input_detector` / `pinyin_converter` (no GUI).
- Pin dependency versions in `requirements.txt` when preparing releases.
- Document known limits: pinyin-only TTS quality, need for ffmpeg on PATH.

---

## Phase 2: English TTS and phonetics — **0%**

**Goals:** English input, reference TTS, and a phonetic breakdown (e.g. IPA or ARPABET) similar to the Mandarin tone view.

**Recommendations:**

- Reuse the same pipeline pattern: **input normalization → display model → `edge-tts` en-US voice → same speed/export UI**.
- Prefer **one engine** for MVP (e.g. `edge-tts` en-US neural) before adding paid APIs.
- IPA generation: consider **`eng-to-ipa`**, **`pronouncing`**, or CMUdict-based helpers; treat homographs as out-of-scope for v1 or use a small user disambiguation hint.
- **UI:** separate tab or stacked “language” selector so Chinese and English logic stay isolated in `core/`.

**Risks:** English stress and weak forms are subtle; start with **word-level** display before phrase-level liaison.

---

## Phase 3: Audiobook / long text mode — **0%**

**Goals:** Paste or load long text; split into sentences/clauses; queue playback with skip and position.

**Recommendations:**

- **Chinese segmentation:** `jieba` or similar for Hanzi sentence boundaries; regex + punctuation rules as fallback.
- **Architecture:** generate audio **per sentence** (or small batch) to bound memory; cache files under `temp_audio/` with LRU or session cap.
- **UI:** list or virtualized table of segments; “play from here”; optional **pause between sentences** for shadowing practice.
- **Edge limits:** batch TTS may hit rate limits; add **delay/backoff** and a clear progress indicator.

---

## Phase 4: User recording and comparison — **0%**

**Goals:** Record microphone audio; compare timing/shape to reference clip; show simple feedback (score or visual).

**Recommendations:**

- Capture: **`sounddevice`** or **PyAudio**; save user WAV aligned to session folder.
- **MVP comparison:** duration + RMS envelope similarity or **DTW** on MFCC features (e.g. **librosa**) before investing in deep models.
- Optional **ASR** (e.g. Whisper local API) for “did you say the right syllable” — higher scope; gate behind Phase 4.1.
- **Privacy:** explicit consent string; delete recordings on exit by default.

---

## Phase 5: Web version — **0%**

**Goals:** Browser UI + backend for synthesis and file handling; parity with core trainer flows where feasible.

**Recommendations:**

- **Backend:** FastAPI (or similar) exposing **synthesize** and **process** endpoints; run **ffmpeg** and `edge-tts` server-side (browser cannot rely on user-installed ffmpeg).
- **Frontend:** React or Vue; reuse **tone display** concepts as components.
- **Security:** auth or API keys if public; **rate limiting**; never trust client for unpaid TTS abuse.
- **Deployment:** document Docker with ffmpeg image; environment variables for voice allowlists.

**Note:** Edge TTS from browsers directly is fragile; **server-side synthesis** matches the current Python architecture.

---

## How to update progress

When a phase ships meaningful scope, bump its **Phase progress** (e.g. 0% → 50% → 100%) and refresh the **Share of whole project** column (phase progress × 20%). Keep the summary table in [README.md](README.md) in sync.
