"""
Phase 0 — Hotkey Validation
Confirms the backtick global hotkey fires correctly without conflicts.

Run this, then use your normal apps (VS Code, terminal, browser, Obsidian).
Press backtick: you should see events logged here, and the backtick should NOT
appear as a typed character in the other app (suppress=True).

Press ESC to exit.
"""

import keyboard
from datetime import datetime


HOTKEY = "`"
press_count = 0
release_count = 0


def on_press(e):
    global press_count
    press_count += 1
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] PRESS  #{press_count}  key={e.name!r}  scan={e.scan_code}")


def on_release(e):
    global release_count
    release_count += 1
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] RELEASE #{release_count}  key={e.name!r}  scan={e.scan_code}")


print(f"Hotkey test — listening for backtick ({HOTKEY!r})")
print("Hold the key, release it, repeat a few times.")
print("Check that backtick does NOT appear in other apps while this is running.")
print("Press ESC to exit.\n")

keyboard.on_press_key(HOTKEY, on_press, suppress=True)
keyboard.on_release_key(HOTKEY, on_release, suppress=True)

keyboard.wait("esc")

print(f"\nDone. {press_count} press(es), {release_count} release(s).")
print("PASS if: counts match, no backtick leaked to other apps, no crashes.")
