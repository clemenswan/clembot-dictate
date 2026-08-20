"""
Windows startup registration via HKCU Run registry key.
No admin required — applies only to the current user.
"""
from __future__ import annotations
import sys
import winreg
from pathlib import Path

TASK_NAME = "Clembot-dictate"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _exe_path() -> str:
    """Absolute path to the running executable (or script in dev mode)."""
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable))
    return str(Path(sys.argv[0]).resolve())


def is_registered() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, TASK_NAME)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


def register() -> bool:
    try:
        exe = _exe_path()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, TASK_NAME, 0, winreg.REG_SZ, f'"{exe}"')
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def unregister() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_WRITE)
        winreg.DeleteValue(key, TASK_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False
