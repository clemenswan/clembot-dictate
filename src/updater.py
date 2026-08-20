"""
Non-blocking version check against a hosted JSON endpoint.
Runs in a daemon thread — never blocks startup, never crashes the app.

Expected JSON at UPDATE_CHECK_URL:
  { "latest": "1.1.0", "url": "https://...", "notes": "What's new..." }

Calls on_update_available(latest, url, notes) on the background thread if
a newer version is found. The callback must be thread-safe (use root.after).
"""

import json
import threading
import urllib.request

from logger import get_logger
from config import VERSION, UPDATE_CHECK_URL

log = get_logger("updater")

_TIMEOUT = 5  # seconds — fast enough to not block UX, long enough for slow connections

# Cloudflare's managed rules 403 the default "Python-urllib/3.x" user agent, and
# wanessalabs.com sits behind them. Measured 2026-08-19: bare urllib got 403 on
# every path of the site, including the homepage, while any named agent got 200.
# Without this header the update check could never succeed, and `except Exception`
# below would have swallowed the 403 forever. Keep it named and honest.
_USER_AGENT = f"Clembot-dictate/{VERSION} (+https://wanessalabs.com)"


def check_for_update(on_update_available):
    """Fire-and-forget version check. Completely silent on failure."""
    threading.Thread(target=_check, args=(on_update_available,), daemon=True).start()


def _check(on_update_available):
    if not UPDATE_CHECK_URL:
        return
    try:
        request = urllib.request.Request(
            UPDATE_CHECK_URL, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        latest = data.get("latest", "").strip()
        url    = data.get("url", "").strip()
        notes  = data.get("notes", "").strip()
        if latest and _is_newer(latest, VERSION):
            log.info("Update available: %s → %s", VERSION, latest)
            on_update_available(latest, url, notes)
        else:
            log.debug("Up to date (%s).", VERSION)
    except Exception as e:
        log.debug("Version check skipped: %s", e)


def _is_newer(latest: str, current: str) -> bool:
    try:
        return (
            tuple(int(x) for x in latest.split("."))
            > tuple(int(x) for x in current.split("."))
        )
    except Exception:
        return False
