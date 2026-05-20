# Building the Windows executable (PyInstaller)

This guide walks through creating a **standalone** `ChinesePronunciationTrainer.exe` folder you can copy to another PC. The repo does **not** commit `dist/` or `build/` (they are gitignored); you build them locally.

## What you need

| Requirement | Notes |
|-------------|--------|
| **Windows 10/11 (64-bit)** | Matches our PyInstaller target. |
| **Python 3.12 (64-bit)** | Recommended; use the [python.org](https://www.python.org/downloads/) installer and tick **“Add python.exe to PATH”**. |
| **Internet** | First run of the app needs network for Edge TTS and translation; the build itself downloads PyPI wheels. |
| **ffmpeg** | **Not** required on PATH for this project: `imageio-ffmpeg` (in `requirements.txt`) ships a static `ffmpeg` used by the app. |

## Step 1 — Clone and open a terminal

```powershell
cd path\to\tts_mandarin
```

Use **PowerShell** or **cmd** from the repository root (where `main.py` lives).

## Step 2 — (Optional) Virtual environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Step 3 — Install dependencies

```powershell
py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install -r requirements.txt
```

## Step 4 — Install PyInstaller

```powershell
py -3.12 -m pip install pyinstaller
```

## Step 5 — Run PyInstaller (onedir)

From the **repo root**, run this **exact** command (line continuation is for PowerShell with backticks):

```powershell
py -3.12 -m PyInstaller main.py `
  --name "ChinesePronunciationTrainer" `
  --windowed `
  --onedir `
  --noconfirm `
  --collect-all jieba `
  --collect-all wordfreq `
  --collect-all pypinyin `
  --collect-all zhconv `
  --collect-all imageio_ffmpeg `
  --collect-data certifi `
  --collect-submodules edge_tts `
  --hidden-import aiohttp `
  --hidden-import aiohttp.resolver `
  --hidden-import aiohttp.connector `
  --hidden-import audioop
```

On **Python 3.13+**, `requirements.txt` installs `audioop-lts` (stdlib `audioop` was removed). Without it, pydub fails at startup with `No module named 'pyaudioop'`.

**Why these flags**

- **`--onedir`** — One folder with `ChinesePronunciationTrainer.exe` plus `_internal\` (recommended for pygame / temp files; avoid `--onefile` for this app).
- **`--windowed`** — No console window behind the GUI.
- **`--collect-all …`** — Pulls data files some packages need at runtime (jieba dict, wordfreq data, bundled ffmpeg, etc.).
- **`--collect-submodules edge_tts`** — Helps catch dynamic imports in `edge-tts`.

PyInstaller may write `ChinesePronunciationTrainer.spec` in the repo root; it is gitignored (`*.spec`).

## Kokoro edition — larger bundle with local TTS

To ship a frozen build that includes **Kokoro** (PyTorch + model runtime), use the **`ChinesePronunciationTrainerKokoro`** target. Output exe:

`dist\ChinesePronunciationTrainerKokoro\ChinesePronunciationTrainerKokoro.exe`

This is the **“Chinese Pronunciation Trainer — Kokoro version”** distribution (same app; **Kokoro** + **Edge** engines inside). The folder is **much larger** than the standard build (torch alone is big); the first launch may still download **Hugging Face** Kokoro weights to the user cache.

From the repo root:

```powershell
.\scripts\build_kokoro_edition.ps1
```

Or paste the equivalent `PyInstaller` command from `scripts/build_kokoro_edition.ps1` (includes `--collect-all kokoro`, `--collect-all torch`, `--collect-all misaki`, etc.).

## Step 6 — Where is the exe?

After a successful build:

```
dist\ChinesePronunciationTrainer\
  ChinesePronunciationTrainer.exe   ← run this
  _internal\                        ← runtime DLLs, Python, bundled ffmpeg, etc.
```

**Important:** Do **not** run the exe under `build\ChinesePronunciationTrainer\`. That directory is only an intermediate PyInstaller staging area and **will not** contain a full `_internal` runtime — you will see errors about missing `python312.dll`.

## Step 7 — Test locally

1. Double-click `dist\ChinesePronunciationTrainer\ChinesePronunciationTrainer.exe`.
2. Try **Play** on a short Hanzi phrase, change speed, open the **Translate** tab.
3. On first run, the app may create next to the exe:
   - `temp_audio\` — temporary WAVs
   - `assets\history.json` — input history (if used)

## Step 8 — Share with others

Zip the **entire** folder `dist\ChinesePronunciationTrainer\` (exe + `_internal` together). Recipients extract the zip and run the `.exe`. They do **not** need Python installed.

They still need:

- **Network** for Edge TTS and Google-based translation (unless you change the app).
- **Windows x64** compatible with the Python version you built with.

## Rebuild after code changes

Run the same PyInstaller command again (`--noconfirm` overwrites `dist\`). You can delete `build\` and `dist\` first if you want a clean tree:

```powershell
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
```

## Run from source (no exe)

If you have Python 3.12 but do not want to build an exe, from the repo root:

```powershell
py -3.12 main.py
```

Or double-click `run.bat` in the repo root (same command + `pause` at the end).

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| `Failed to load python312.dll` under `build\...` | Run the exe under **`dist\ChinesePronunciationTrainer\`**, not `build\`. |
| `No module named 'pyaudioop'` / `audioop` | Build on 3.13+ needs `pip install audioop-lts` and `--hidden-import audioop` (included above). |
| Missing module at runtime | Add `--hidden-import packagename` to the command and rebuild. |
| `pyi_rth_nltk` / `name 'obj' is not defined` on Kokoro exe startup | NLTK is not used by this app; rebuild with `scripts/build_kokoro_edition.ps1` (includes `--exclude-module nltk`). |
| Kokoro: `Cannot log to objects of type 'NoneType'` | Windowed exe has no stderr; fixed in `main.py` — **rebuild** the Kokoro edition after pulling latest `main`. |
| Kokoro: `name 'name' is not defined` (torch._numpy) | Run `scripts/build_kokoro_edition.ps1` (patches torch then rebuilds). Needs **internet** on first Kokoro run for HF model weights. |
| `py` not found | Install Python from python.org and use **“py launcher”**, or replace `py -3.12` with the full path to `python.exe`. |

For older setup notes about a **system** ffmpeg on PATH, see [setup_ffmpeg.md](../setup_ffmpeg.md); the bundled binary is preferred for normal use.
