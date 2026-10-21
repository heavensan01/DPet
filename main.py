import os
import sys
import tempfile
from pathlib import Path

from paths import APP_DIR, DATA_DIR

ROOT = APP_DIR
os.chdir(APP_DIR)

# pythonw.exe has no console: send output to a log file instead of crashing
if sys.stdout is None or sys.stderr is None:
    _log = open(DATA_DIR / "dpet.log", "a", buffering=1, encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _log
    if sys.stderr is None:
        sys.stderr = _log

from PySide6.QtCore import QLockFile, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

import sprites
from config import Config
from pet import PetWindow
from render import grid_to_image

PID_FILE = DATA_DIR / "dpet.pid"


def make_icon():
    img = grid_to_image(sprites.frame("idle", 0))
    pm = QPixmap.fromImage(img).scaled(64, 64, Qt.KeepAspectRatio, Qt.FastTransformation)
    return QIcon(pm)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    lock = QLockFile(os.path.join(tempfile.gettempdir(), "dpet_single_instance.lock"))
    if not lock.tryLock(200):
        lock.removeStaleLockFile()
        if not lock.tryLock(200):
            return                        # already running: do nothing

    PID_FILE.write_text(str(os.getpid()))
    app.aboutToQuit.connect(lambda: PID_FILE.unlink(missing_ok=True))

    cfg = Config()
    tray = QSystemTrayIcon(make_icon(), app)
    pet = PetWindow(cfg, tray)

    menu = QMenu()
    menu.addAction("Show / Hide", lambda: pet.setVisible(not pet.isVisible()))
    menu.addAction("Feed", pet.feed)
    menu.addAction("Run on the wheel", pet.go_run)
    menu.addAction("Drink water", pet.go_drink)
    menu.addAction("Refill water", pet.refill_water)
    menu.addSeparator()
    menu.addAction("Quit", app.quit)
    tray.setContextMenu(menu)
    tray.setToolTip(cfg["pet_name"])
    tray.show()

    pet.show_all()
    from datetime import datetime
    hour = datetime.now().hour
    if 5 <= hour < 12:
        pet.say("Good Morning!", "morning", 4000)
    elif hour >= 22 or hour < 5:
        pet.say("Good Night!", "night", 4000)
    else:
        pet.say("Hello!", "hello", 4000)
    code = app.exec()
    lock.unlock()
    sys.exit(code)


if __name__ == "__main__":
    main()
