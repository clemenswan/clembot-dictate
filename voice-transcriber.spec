# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for Clembot-dictate.
#
# Build: pyinstaller voice-transcriber.spec --clean
# Output: dist/Clembot-dictate/Clembot-dictate.exe
#
# Known issues addressed here:
#   - customtkinter: theme JSON + fonts not auto-collected
#   - ctranslate2 / faster_whisper: native CTranslate2 DLLs
#   - sounddevice: PortAudio DLL
#   - soundfile: libsndfile DLL
#   - pywin32: pywintypes DLL + hidden imports
#   - pystray: Windows backend not found without hidden import
#
# NOT bundled (downloaded at runtime):
#   - faster-whisper model files (~74 MB for tiny)
#     Stored in: %USERPROFILE%\.cache\huggingface\hub\
#     Downloaded automatically on first run if not present.

from PyInstaller.utils.hooks import collect_all, collect_data_files

# ── Collect packages that ship data files or native extensions ──────────────
datas    = []
binaries = []
hiddenimports = []

for pkg in ("customtkinter", "ctranslate2", "faster_whisper", "sounddevice", "soundfile"):
    d, b, h = collect_all(pkg)
    datas    += d
    binaries += b
    hiddenimports += h

# ── Analysis ─────────────────────────────────────────────────────────────────
a = Analysis(
    ["src/main.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        # Windows API
        "win32gui",
        "win32process",
        "win32con",
        "win32api",
        "pywintypes",
        # System monitoring
        "psutil",
        "psutil._pswindows",
        # Tray icon Windows backend
        "pystray._win32",
        # PIL
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageTk",
        # Core deps
        "pyperclip",
        "pyautogui",
        "keyboard",
        "numpy",
        # Optional AI backends — imported dynamically; include so the exe
        # doesn't crash if the user switches backend at runtime.
        "anthropic",
        "httpx",
        "httpcore",
        "anyio",
        "ollama",
        # Windows Credential Manager wrapper for API key storage
        "keyring",
        "keyring.backends.Windows",
    ],
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
    [],
    exclude_binaries=True,
    name="Clembot-dictate",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No black console window on launch
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Clembot-dictate",
)
