# Build "Chinese Pronunciation Trainer — Kokoro edition" (Windows onedir)
# Output: dist\ChinesePronunciationTrainerKokoro\ChinesePronunciationTrainerKokoro.exe
# Requires: py -3.12, pip install -r requirements.txt, pip install pyinstaller
# Bundle is LARGE (torch + kokoro). First app run may still download model weights.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Remove-Item -Recurse -Force dist\ChinesePronunciationTrainerKokoro, build\ChinesePronunciationTrainerKokoro -ErrorAction SilentlyContinue

# PyInstaller breaks ``for name in ...: vars()[name] = ...`` in torch._numpy._ufuncs.
py -3.12 scripts\patch_torch_ufuncs.py

# NLTK is often installed globally (e.g. open-interpreter) but this app does not use it.
# PyInstaller's pyi_rth_nltk hook crashes at startup (NameError: obj) — exclude it.
py -3.12 -m PyInstaller main.py `
  --runtime-hook hooks\rthook_torch_dynamo.py `
  --name "ChinesePronunciationTrainerKokoro" `
  --windowed `
  --onedir `
  --noconfirm `
  --exclude-module nltk `
  --collect-all jieba `
  --collect-all wordfreq `
  --collect-all pypinyin `
  --collect-all zhconv `
  --collect-all imageio_ffmpeg `
  --collect-all kokoro `
  --collect-all torch `
  --collect-all misaki `
  --collect-all espeakng_loader `
  --collect-all phonemizer `
  --collect-all pypinyin_dict `
  --collect-all language_tags `
  --collect-data certifi `
  --collect-submodules edge_tts `
  --collect-submodules torch `
  --hidden-import aiohttp `
  --hidden-import aiohttp.resolver `
  --hidden-import aiohttp.connector `
  --hidden-import audioop `
  --hidden-import loguru

Write-Host "Done. Run: dist\ChinesePronunciationTrainerKokoro\ChinesePronunciationTrainerKokoro.exe"
