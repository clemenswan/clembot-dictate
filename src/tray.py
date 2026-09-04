"""
System tray icon — pystray + Pillow.
Two visual states: idle (brand green) and recording (brand red).
Menu: Show History, Clean clipboard, Clipboard only, Quit.
"""

from __future__ import annotations

import theme
import threading
from typing import Callable

from PIL import Image, ImageDraw
import pystray

from logger import get_logger

log = get_logger("tray")

def _rgba(hex_color: str, alpha: int = 255) -> tuple:
    """theme.py speaks CSS hex; Pillow wants a tuple. One conversion, one source."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


SIZE = 64   # icon canvas size
DOT  = 20   # inner dot radius


def _make_icon(recording: bool) -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer circle
    bg = _rgba(theme.RECORDING) if recording else _rgba(theme.ACCENT)
    draw.ellipse([2, 2, SIZE - 2, SIZE - 2], fill=bg)

    # Inner mic dot
    cx, cy = SIZE // 2, SIZE // 2
    r = DOT // 2
    dot_color = _rgba(theme.BG)
    draw.ellipse([cx - r, cy - r - 4, cx + r, cy + r - 4], fill=dot_color)

    # Mic stand line
    draw.rectangle([cx - 1, cy + r - 4, cx + 1, cy + r + 6], fill=dot_color)
    draw.arc([cx - 8, cy - 2, cx + 8, cy + 14], start=0, end=180, fill=dot_color, width=2)

    return img


class TrayIcon:
    def __init__(self, on_show: Callable, on_quit: Callable,
                 on_clipboard_toggle: Callable | None = None,
                 on_clean: Callable | None = None):
        self._on_show = on_show
        self._on_quit = on_quit
        self._on_clipboard_toggle = on_clipboard_toggle
        self._on_clean = on_clean
        self._recording = False
        self._clipboard_only = False

        self._icon = pystray.Icon(
            name="VoiceTranscriber",
            icon=_make_icon(False),
            title="Clembot-dictate",
            menu=pystray.Menu(
                pystray.MenuItem("Show History", self._handle_show, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Clean clipboard",
                    self._handle_clean,
                    visible=lambda item: self._on_clean is not None,
                ),
                pystray.MenuItem(
                    "Clipboard only",
                    self._handle_clipboard_toggle,
                    checked=lambda item: self._clipboard_only,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self._handle_quit),
            ),
        )

    def run_detached(self):
        """Start tray in a background thread."""
        t = threading.Thread(target=self._icon.run, daemon=True)
        t.start()

    def set_recording(self, recording: bool):
        self._recording = recording
        self._icon.icon = _make_icon(recording)
        self._icon.title = "Clembot-dictate — Recording..." if recording else "Clembot-dictate"

    def notify(self, message: str, title: str = "Clembot-dictate") -> None:
        try:
            self._icon.notify(message, title)
        except Exception as e:
            log.warning("Tray notification failed: %s", e)

    @property
    def clipboard_only(self) -> bool:
        return self._clipboard_only

    def stop(self):
        self._icon.stop()

    def _handle_clipboard_toggle(self, icon, item):
        self._clipboard_only = not self._clipboard_only
        log.info("Clipboard-only mode %s", "on" if self._clipboard_only else "off")
        if self._on_clipboard_toggle:
            self._on_clipboard_toggle(self._clipboard_only)

    def _handle_clean(self, icon, item):
        if self._on_clean:
            self._on_clean()

    def _handle_show(self, icon, item):
        self._on_show()

    def _handle_quit(self, icon, item):
        self._on_quit()
