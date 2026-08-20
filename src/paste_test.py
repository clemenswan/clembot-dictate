"""
Phase 0 — Paste Path Validation
Confirms pyperclip + pyautogui can paste into the active window.

How to use:
1. Run this script.
2. When prompted, click into the target app (Notepad, VS Code, browser, etc.)
   and position your cursor where you want text to appear.
3. Press Enter here to trigger the paste.
4. Verify the test string appears at the cursor.

Repeat for each app you care about: Notepad, VS Code, Obsidian, Chrome, terminal.
"""

import pyperclip
import pyautogui
import time

TEST_STRING = "[PASTE TEST] voice-transcriber Phase 0 — if you see this, paste works."

PAUSE_SECONDS = 3  # time to switch to target app after pressing Enter


def run_paste_test(app_name: str):
    input(f"\nTarget: {app_name}\n  → Click into {app_name} and position cursor, then press Enter here...")
    print(f"  Pasting in {PAUSE_SECONDS}s — switch to {app_name} now...")
    time.sleep(PAUSE_SECONDS)

    pyperclip.copy(TEST_STRING)
    pyautogui.hotkey("ctrl", "v")

    result = input("  Did the text appear correctly? [y/n]: ").strip().lower()
    status = "PASS" if result == "y" else "FAIL"
    print(f"  {status}: {app_name}")
    return status


apps = [
    "Notepad",
    "VS Code",
    "Obsidian",
    "Chrome (address bar or text field)",
    "Windows Terminal / PowerShell",
]

print("Paste path test — pyperclip + pyautogui")
print("Testing each app in sequence.\n")

results = {}
for app in apps:
    skip = input(f"Test {app}? [y/n]: ").strip().lower()
    if skip != "y":
        results[app] = "SKIPPED"
        continue
    results[app] = run_paste_test(app)

print("\n--- Results ---")
for app, status in results.items():
    print(f"  {status:<8} {app}")

fails = [a for a, s in results.items() if s == "FAIL"]
if fails:
    print(f"\nFailed in: {', '.join(fails)}")
    print("These apps may have focus or privilege issues. Document in docs/setup.md.")
else:
    print("\nAll tested apps PASS.")
