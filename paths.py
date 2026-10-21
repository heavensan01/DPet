"""Where things live. Source run: next to the code. Installed .exe: settings go to %APPDATA%\\DPet
(always writable, even when the app is installed under Program Files)."""
import os
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))   # bundled code + assets

if FROZEN:
    DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "DPet"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
else:
    DATA_DIR = Path(__file__).resolve().parent
