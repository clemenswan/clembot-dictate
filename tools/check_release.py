"""Release preflight: does this tree actually describe one coherent release?

Four files name the version and they drift, because bumping one is a manual step
and nothing fails when you miss it. The 1.1.0 build shipped with three files still
saying 1.0.0. This reads all four and refuses to agree with itself quietly.

It also checks the two things that decide whether an update can reach anyone:
the installer's size against Cloudflare Pages' 25 MiB per-asset limit, and, with
--endpoint, what the live update manifest actually serves.

Stdlib only, so it runs anywhere the app does:

    python tools/check_release.py
    python tools/check_release.py --endpoint     # also hits the network
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES_ASSET_LIMIT = 25 * 1024 * 1024      # Cloudflare Pages: 25 MiB per file
TIMEOUT = 10

problems: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    problems.append(msg)


def note(msg: str) -> None:
    notes.append(msg)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def find(pattern: str, text: str, where: str) -> str | None:
    # MULTILINE, because every pattern here anchors to the start of a line and
    # `^` without it matches only the start of the file. Without this the tool
    # reported "no version found" for a file that plainly has one.
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        fail(f"{where}: could not find a version at all (pattern {pattern!r})")
        return None
    return match.group(1)


# ---------------------------------------------------------------------------
# 1. The four places a version is written
# ---------------------------------------------------------------------------

def collect_versions() -> tuple[str | None, dict[str, str | None]]:
    config_version = find(r'^VERSION\s*=\s*"([^"]+)"', read("src/config.py"), "src/config.py")
    found = {
        "src/config.py": config_version,
        "installer.iss": find(r'#define AppVersion "([^"]+)"', read("installer.iss"), "installer.iss"),
    }
    try:
        manifest = json.loads(read("distribution/version.json"))
        found["distribution/version.json"] = str(manifest.get("latest", "")).strip() or None
        if not manifest.get("url", "").strip():
            fail("distribution/version.json: no download url, so an update banner would lead nowhere")
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"distribution/version.json: unreadable ({exc})")
        found["distribution/version.json"] = None

    # build.bat prints the installer name; a stale string here misleads whoever
    # reads the console after a build, which is the only report that build gives.
    build = read("build.bat")
    stamped = sorted(set(re.findall(r"Clembot-dictate-Setup-([0-9][^.\s]*\.[^.\s]*\.[^.\s]*)\.exe", build)))
    found["build.bat"] = stamped[0] if len(stamped) == 1 else (", ".join(stamped) or None)

    for where, value in found.items():
        if value is None:
            fail(f"{where}: no version found")

    if config_version and any(v and v != config_version for v in found.values()):
        drifted = [f"{k} = {v}" for k, v in found.items() if v and v != config_version]
        fail("version drift, config.py is the source of truth ("
             + f"{config_version}): " + "; ".join(drifted))
    return config_version, found


# ---------------------------------------------------------------------------
# 2. The artifact this release claims to be
# ---------------------------------------------------------------------------

def check_artifact(version: str | None) -> None:
    if not version:
        return
    installer = ROOT / "dist" / f"Clembot-dictate-Setup-{version}.exe"
    if not installer.is_file():
        fail(f"no installer built for {version}: {installer.relative_to(ROOT)} is missing")
        return
    size = installer.stat().st_size
    note(f"installer {installer.name}: {size / 1024 / 1024:.1f} MiB")
    if size > PAGES_ASSET_LIMIT:
        note("that is over Cloudflare Pages' 25 MiB per-asset limit, so the download "
             "cannot live on the Pages site. Host the binary elsewhere (R2, or a "
             "GitHub release) and point version.json at it.")

    stale = sorted(p.name for p in (ROOT / "dist").glob("Clembot-dictate-Setup-*.exe")
                   if p.name != installer.name)
    if stale:
        note("older installers still in dist/, easy to upload by mistake: " + ", ".join(stale))


# ---------------------------------------------------------------------------
# 3. What the live endpoint actually serves
# ---------------------------------------------------------------------------

def app_user_agent(version: str | None) -> str:
    """The header the app itself sends, read from updater.py so it cannot drift.

    Checking the endpoint with a different agent than the app uses would prove
    nothing: Cloudflare 403s the default Python one, which is how a permanently
    broken update check looked healthy from a browser."""
    updater = read("src/updater.py")
    if "User-Agent" not in updater:
        fail("src/updater.py sends no User-Agent: Cloudflare 403s Python's default, "
             "and the update check swallows the error, so it fails silently forever")
        return "Python-urllib/3"
    template = find(r'^_USER_AGENT\s*=\s*f?"([^"]+)"', updater, "src/updater.py") or ""
    return template.replace("{VERSION}", version or "")


def fetch(url: str, agent: str, method: str = "GET"):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": agent}, method=method),
        timeout=TIMEOUT)


def check_endpoint(version: str | None) -> None:
    url = find(r'^UPDATE_CHECK_URL\s*=\s*"([^"]*)"', read("src/config.py"), "src/config.py")
    if not url:
        note("UPDATE_CHECK_URL is empty: the update check is disabled by design")
        return
    agent = app_user_agent(version)
    note(f"update endpoint: {url}")
    note(f"probing as the app does, User-Agent: {agent}")
    try:
        with fetch(url, agent) as resp:
            served = json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        fail(f"update endpoint returns HTTP {exc.code}: no existing install can learn "
             f"about {version or 'this release'}")
        return
    except Exception as exc:                       # network, DNS, TLS, bad JSON
        fail(f"update endpoint unreachable or not JSON: {exc}")
        return

    latest = str(served.get("latest", "")).strip()
    note(f"endpoint serves latest = {latest or '(none)'}")
    if version and latest != version:
        fail(f"endpoint serves {latest!r} but this tree builds {version!r}")

    download = str(served.get("url", "")).strip()
    if not download:
        fail("endpoint has no download url")
        return
    try:
        with fetch(download, agent, method="HEAD") as resp:
            note(f"download url HTTP {resp.status}: {download}")
    except urllib.error.HTTPError as exc:
        fail(f"download url returns HTTP {exc.code}: the update banner would lead "
             f"users to a dead link ({download})")
    except Exception as exc:
        fail(f"download url unreachable: {download} ({exc})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", action="store_true",
                        help="also check the live update manifest and download link")
    args = parser.parse_args()

    version, found = collect_versions()
    print("Versions found")
    for where, value in found.items():
        print(f"  {value or '?':<10} {where}")
    print()

    check_artifact(version)
    if args.endpoint:
        check_endpoint(version)

    for line in notes:
        print(f"note: {line}")
    if problems:
        print()
        for line in problems:
            print(f"FAIL: {line}")
        print(f"\n{len(problems)} problem(s). This is not a releasable tree.")
        return 1
    print(f"\nConsistent at {version}. Releasable as far as this check can tell; "
          "the manual checks in the release docs are the rest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
