# PyInstaller runtime hook — must run before torch is imported.
import os

os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")
