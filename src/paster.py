"""
Clipboard write + paste to active window.
Saves and restores the previous clipboard content so dictation doesn't clobber it.
"""

import time
import pyperclip
import pyautogui


# Small delay to ensure the key-release event has fully cleared before we send Ctrl+V.
# Without this, some apps intercept the paste before focus is restored.
PASTE_DELAY = 0.05  # seconds


def paste(text: str, clipboard_only: bool = False):
    """Copy text to clipboard and optionally auto-paste into the active window.

    When clipboard_only=True the text is placed on the clipboard and the
    function returns immediately — no Ctrl+V, no previous-clipboard restore.
    The user pastes manually.
    """
    if not text:
        return

    if clipboard_only:
        pyperclip.copy(text)
        return

    # Save whatever was in the clipboard before we clobber it.
    try:
        previous = pyperclip.paste()
    except Exception:
        previous = ""

    pyperclip.copy(text)
    time.sleep(PASTE_DELAY)
    pyautogui.hotkey("ctrl", "v")

    # Restore previous clipboard content after a brief pause.
    time.sleep(PASTE_DELAY)
    try:
        pyperclip.copy(previous)
    except Exception:
        pass
