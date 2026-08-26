from pathlib import Path


project_root = Path(SPECPATH)
data_files = [
    ("index.html", "."),
    ("RoboFace.lottie", "."),
    ("vendor/dotlottie-wc.js", "vendor"),
    ("vendor/dotlottie-player.wasm", "vendor"),
    ("vendor/LICENSE.dotlottie-wc.txt", "vendor"),
]

a = Analysis(
    ["launcher.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=data_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="roboface-linux-arm64",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)