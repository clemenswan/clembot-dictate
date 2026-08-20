"""
Centralized logging for Clembot-dictate.

Log file: %APPDATA%\\Roaming\\Clembot-dictate\\logs\\clembot-dictate.log
Rotating: 1 MB max, 3 backups kept.
Console output is active when a terminal is attached (dev mode).

Usage in each module:
    from logger import get_logger
    log = get_logger("recorder")
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


_LOG_DIR = Path.home() / "AppData" / "Roaming" / "Clembot-dictate" / "logs"
_LOG_FILE = _LOG_DIR / "clembot-dictate.log"

_root = logging.getLogger("clembot")
_root.setLevel(logging.DEBUG)

_fmt = logging.Formatter(
    "%(asctime)s [%(levelname)-5s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

try:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _fh = RotatingFileHandler(
        _LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    _fh.setLevel(logging.DEBUG)
    _fh.setFormatter(_fmt)
    _root.addHandler(_fh)
except Exception:
    pass  # Can't write logs — app still runs without them

# Console handler only when a terminal is actually attached (dev mode).
# In a PyInstaller console=False bundle, sys.stdout is None.
if sys.stdout is not None:
    _ch = logging.StreamHandler(sys.stdout)
    _ch.setLevel(logging.DEBUG)
    _ch.setFormatter(_fmt)
    _root.addHandler(_ch)


def get_logger(name: str) -> logging.Logger:
    return _root.getChild(name)
