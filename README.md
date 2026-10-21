# 🐹 DPet – Pixel Hamster Desktop Pet

A tiny pixel-art hamster that lives on your Windows desktop. It walks around, eats, naps,
jumps, runs on its spinning wheel and drinks from its water bottle, and it reminds you to
drink water and take breaks.

![DPet hamster](screenshots/hamster.png)

## Features
- **Pixel-art animations:** 4-frame walk cycle, eating, sitting, napping (Zzz) and jumping
- **Spinning wheel:** the hamster climbs in, the wheel spins up while it runs, then it steps out
- **Water bottle:** the nozzle turns toward the screen centre, and the hamster reaches up and drinks
- **Small speech bubble** above its head for every message
- **Reminders:** water, study breaks and bedtime
- **Drag and drop:** move the hamster, wheel and bottle anywhere along the bottom of the screen
- **Right-click menu:** feed, go run, go drink, refill water, resize, quit

## Screenshots
| Hamster | Wheel | Water bottle |
|---|---|---|
| ![Hamster](screenshots/hamster.png) | ![Wheel](screenshots/wheel.png) | ![Water bottle](screenshots/water.png) |

## Download (Windows)
Get **`DPet-Setup.exe`** from the [Releases page](../../releases/latest) and run it.
`DPet-portable.zip` is the no-install version.

> Windows may show a "Windows protected your PC" box because the app is not code-signed.
> Click **More info → Run anyway**.

## How to use
- **Click** the hamster: happy face. **Drag:** move it. **Right-click:** menu.
- Right-click → **Go run on the wheel** or **Go drink water** to send it there now.
- It also goes by itself: to the wheel every 3–6 minutes and to the bottle every 5–9 minutes.
- When the bottle is empty, use **Refill water**.
- Settings are saved in `%APPDATA%\DPet\config.json`.

## Run from source
```
pip install -r requirements.txt
python main.py
```
Needs Python 3.10+.

## Build the app yourself
Double-click `BUILD DESKTOP APP.bat` (needs Python only for building).
- `dist\DPet\DPet.exe` – the standalone app
- With [Inno Setup 6](https://jrsoftware.org/isdl.php) installed, the same file also makes
  `installer_output\DPet-Setup.exe`.

Pushing a tag such as `v1.0` also builds the installer automatically with GitHub Actions.

## Settings (`config.json`)
- `scale`: 1.25 tiny / 1.5 small (default) / 2 medium / 3 large
- `speed`: walking speed
- `activity_gap_seconds`, `jump_gap_seconds`: time between activities and jumps
- `wheel_gap_minutes`, `drink_gap_minutes`, `wheel_run_seconds`: how often and how long
- `wheel_on`, `bottle_on`: show or hide the props
- `water_minutes`, `study_minutes`, `sleep_time`: reminders

## Built with
Python · PySide6 (Qt) · PyInstaller · Inno Setup · GitHub Actions