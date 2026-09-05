"""Render the real UI with fake data, screenshot it, and exit.

A design pass that is only ever reviewed by reading the diff is a design pass done
blind. The vault has already paid for that lesson once: a 44px control audit passed
every control while the rows they sat in were unusable, because measuring elements
never measures the arrangement.

This builds the actual `HistoryWindow`, not a mock of it, so what gets photographed
is what ships. It cannot run alongside the installed app under the same hotkey, so it
binds nothing: no keyboard hook, no recorder, no tray.

    python tools/ui_preview.py                 # compact bar
    python tools/ui_preview.py --state all     # every state, one PNG each
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import theme                       # noqa: E402
from history import History, Entry  # noqa: E402
from ui import HistoryWindow        # noqa: E402

SAMPLES = [
    ("um so like can you uh fix the the auth bug from yesterday please",
     "Fix the authentication bug introduced in yesterday's commit."),
    ("okay so what I want is a a list of everything that's blocked right now",
     "List everything currently blocked."),
    ("send wanessa a note that the the deploy went out and the tests are green",
     "Email Wanessa: the deploy shipped and the test suite is green."),
]


def empty_history() -> History:
    """A History with nothing in it, and no path, for the empty-state shot.

    Same __new__ trick as seed() and for the same reason: History() writes to
    the real %APPDATA% file, which this harness once did to a real person.
    """
    import threading
    history = History.__new__(History)
    history._lock = threading.Lock()
    history._entries = []
    return history


def seed() -> History:
    r"""An in-memory History that cannot touch the real file.

    `History()` takes no path and writes straight to
    %APPDATA%\Clembot-dictate\history.json. An earlier version of this harness
    called it directly and wrote nine fake dictations into a real person's history
    before anyone noticed. A preview tool has no business writing anything.
    """
    history = History.__new__(History)          # skip __init__, so no load and no path
    import threading
    history._lock = threading.Lock()
    history._entries = [
        Entry(timestamp=datetime.now().replace(minute=m).isoformat(), text=refined, raw=raw)
        for m, (raw, refined) in enumerate(SAMPLES)
    ]
    history._save = lambda *_args, **_kwargs: None   # belt as well as braces
    return history


def shoot(window: HistoryWindow, name: str, out: Path):
    """Grab the window itself, not the screen, so the frame is exactly the app."""
    from PIL import ImageGrab
    root = window._root
    # Pump the loop rather than sleeping through it. The cards size themselves in
    # an after(120) callback, and time.sleep() blocks Tk's event loop, so a
    # sleeping harness photographs every text block at its untrimmed height and
    # invents a layout bug that is not in the app.
    deadline = time.time() + 0.8
    while time.time() < deadline:
        root.update()
        time.sleep(0.02)
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    shot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.png"
    shot.save(path)
    print(f"{path}  {w}x{h}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default="compact",
                        choices=("compact", "recording", "history", "empty", "settings", "all"))
    parser.add_argument("--out", default=str(ROOT / "docs" / "ui"))
    args = parser.parse_args()

    out = Path(args.out)
    # The empty state needs a window with no history behind it, and it is the
    # only onboarding surface the app has, so it gets rendered like any other.
    entries = empty_history() if args.state in ("empty",) else seed()
    window = HistoryWindow(entries, on_run_ai=lambda *_: None,
                           on_rebind=lambda *_: True)
    window._root.deiconify()
    window._root.update()

    wanted = ("compact", "recording", "history") if args.state == "all" else (args.state,)

    if "compact" in wanted:
        shoot(window, "01-compact", out)

    if "recording" in wanted:
        window._do_set_recording(True)
        shoot(window, "02-recording", out)
        window._do_set_recording(False)

    if "history" in wanted:
        window._toggle_history()
        shoot(window, "03-history", out)
        window._toggle_history()

    if "empty" in wanted:
        window._toggle_history()
        shoot(window, "05-empty", out)
        window._toggle_history()

    if args.state == "settings":
        window._open_settings()
        dialog = None
        deadline = time.time() + 2.0
        while time.time() < deadline and dialog is None:
            window._root.update()
            for child in window._root.winfo_children():
                if child.winfo_class() in ("Toplevel", "CTkToplevel") and child.winfo_ismapped():
                    dialog = child
                    break
            time.sleep(0.05)
        if dialog is None:
            print("settings dialog never appeared")
            return 1
        # Raise it and let the compositor settle, otherwise ImageGrab photographs
        # whatever is sitting at those screen coordinates instead. It did exactly
        # that once and returned somebody's Slack window.
        dialog.lift()
        dialog.attributes("-topmost", True)
        deadline = time.time() + 1.0
        while time.time() < deadline:
            window._root.update()
            time.sleep(0.02)
        from PIL import ImageGrab
        x, y = dialog.winfo_rootx(), dialog.winfo_rooty()
        w, h = dialog.winfo_width(), dialog.winfo_height()
        if w < 50 or h < 50:
            print(f"dialog reports a nonsense size: {w}x{h}")
            return 1
        out.mkdir(parents=True, exist_ok=True)
        ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(out / "04-settings.png")
        print(f"{out / '04-settings.png'}  {w}x{h}")

    window._root.destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
