# DPET - Pixel Hamster Desktop Pet (Windows)

Built from your hamster character sheet, speech-bubble sticker sheet, and the walking,
eating, wheel and water-bottle animation sheets.

## First time
1. Install Python 3.10+ (tick "Add Python to PATH").
2. Double-click **1 SETUP (first time only).bat** (downloads PySide6, ~80 MB, long timeout).

## Every day (no VS Code needed)
- **2 START DPET.bat**  - starts the hamster in the background. Closing VS Code
  or any window does NOT stop it.
- **3 STOP DPET.bat**   - stops it. (Or right-click the hamster > Quit, or tray icon > Quit.)
- **4 AUTO-START with Windows (optional).bat** - starts it every time you log in.
  **5 REMOVE auto-start.bat** undoes that.

Starting it twice is safe: the second copy exits silently.
Errors (if any) are written to `dpet.log`.

## What the hamster does
- Walks with a 4-frame walk cycle on four tiny paws, then every 40-100 s does one
  activity: sits and looks around, eats, or naps (Zzz). Jumps now and then.
- Eating follows the 8-frame sheet: notices food > sniffs > picks up > bites > chews >
  pauses > licks paws > done (happy heart).
- Click: happy face. Drag: move it. Right-click: menu.

## Spinning wheel and water bottle
Both appear near the bottom-right corner by default (right-click the hamster >
**Spinning wheel** / **Water bottle** to show or hide them).
- **Drag and drop** either one anywhere. It drops to the floor (the bottle hangs at the
  right height). A moment after you put one down, the hamster walks over to try it.
- **It uses them by itself:** every 3-6 minutes it runs on the wheel and every 5-9 minutes
  it goes to drink (change in `config.json`). The 45-minute water reminder also sends it
  to the bottle.
- **Wheel:** walks over, climbs in, the wheel spins up while it runs, slows down, and the
  hamster steps out (exit animation). If the wheel is against a screen edge it turns
  round and leaves the other way.
- **Bottle:** the hamster reaches up, grabs the nozzle and drinks (bubbles); the water
  level falls a little each time. When it is empty use **Refill water**.
- **Commands:** right-click > **Go run on the wheel** / **Go drink water** (also in the tray
  menu). If it is busy it finishes the current move first - e.g. it climbs out of the wheel,
  then walks to the bottle - and the same the other way round.
- Positions and water level are remembered in `config.json`.

## If the terminal opens and closes
1. Extract the zip fully first (do not run files from inside the zip).
2. Run **1 SETUP (first time only).bat** on that computer and wait for "Setup finished".
   (Never copy a `.venv` folder between computers; SETUP rebuilds it.)
3. Then run **2 START DPET.bat**.
4. Still not working? Run **DEBUG (shows errors).bat** and send a screenshot.

## Settings: config.json
- `scale` 1.25 tiny / 1.5 small (default) / 2 medium / 3 large (also in right-click > Size)
- `speed` walking speed
- `activity_gap_seconds` [min, max] walking time between activities
- `jump_gap_seconds` [min, max]
- `wheel_gap_minutes` [min, max] how often it goes to the wheel by itself
- `drink_gap_minutes` [min, max] how often it goes to drink by itself
- `wheel_run_seconds` [min, max] how long it runs on the wheel
- `wheel_on`, `bottle_on` show/hide the props; `wheel_x`, `bottle_x` saved positions
  (null = bottom-right corner); `water_level` 0-1
- `water_minutes`, `study_minutes`, `sleep_time`

## Rebuilding sprites
- `python tools/make_props.py climb.png wheel.png bottle.png drink.png exit.png`
  (sheets are in `reference/`) rebuilds the wheel / bottle sprites and the climbing,
  exit and drinking frames.
- `python tools/make_walk.py walk_sheet.png`, `python tools/make_eat.py eating_sheet.png`,
  `python tools/make_sprites.py Hamster_Pixel-Art_Character_Sheet.png` rebuild the rest.
  (They need pillow, numpy, scipy.)

## Build as a real desktop app (Windows)
Double-click `BUILD DESKTOP APP.bat` (needs Python only for building).
- `dist\DPet\DPet.exe` - the standalone app (copy the whole `DPet` folder anywhere).
- Install Inno Setup 6 first and the same file also makes `installer_output\DPet-Setup.exe`
  (Start Menu + desktop shortcut, optional start with Windows, uninstaller).
Installed copies keep their settings in `%APPDATA%\DPet`.
