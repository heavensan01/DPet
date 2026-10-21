# PyInstaller spec: builds dist\DPet\DPet.exe (windowed, no console)
block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=["."],
    datas=[("assets", "assets")],
    hiddenimports=[],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQml",
              "PySide6.QtQuick", "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtCharts"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="DPet",
    console=False,                  # no black terminal window
    icon="packaging/dpet.ico",
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="DPet", upx=False)
