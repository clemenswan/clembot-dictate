"""
Auto-context from active window.

On hotkey press, detects which process owns the foreground window and maps
it to a context mode defined in config.WINDOW_MAP.

Falls back to AUTO_CONTEXT_FALLBACK if no match or if detection fails.
Returns None if AUTO_CONTEXT is disabled.

Requires: pywin32, psutil
"""

from __future__ import annotations

from logger import get_logger
from config import AUTO_CONTEXT, WINDOW_MAP, AUTO_CONTEXT_FALLBACK

log = get_logger("window_detector")


def get_context_for_active_window() -> str | None:
    """
    Return the context mode matching the foreground window's process,
    or None if auto-context is off or detection fails.
    """
    if not AUTO_CONTEXT:
        return None

    try:
        import win32gui
        import win32process
        import psutil

        hwnd     = win32gui.GetForegroundWindow()
        _, pid   = win32process.GetWindowThreadProcessId(hwnd)
        proc     = psutil.Process(pid).name().lower()
        mode     = WINDOW_MAP.get(proc, AUTO_CONTEXT_FALLBACK)
        log.debug("%r → %r", proc, mode)
        return mode

    except ImportError:
        log.warning("pywin32 or psutil not installed — auto-context disabled. Run: pip install pywin32 psutil")
        return None

    except Exception as e:
        log.warning("Detection failed (%s) — using current mode.", e)
        return None
