# Building and releasing

How the EXE and the installer are produced, and the two constraints that decide how a
release gets to anyone.

---

## Preflight

```bash
python tools/check_release.py            # offline: versions and artifacts
python tools/check_release.py --endpoint # also probes the live update manifest
```

Four separate files name the version: `src/config.py`, `installer.iss`,
`distribution/version.json` and `build.bat`. Bumping them is manual, nothing fails when
you miss one, and a release once shipped with three of them still naming the previous
version. This reads all four, compares them, checks the installer exists, and flags older
installers still sitting in `dist/` where they are easy to upload by mistake.

With `--endpoint` it fetches the update manifest **using the user agent read out of
`src/updater.py`**. That detail is the point of the tool rather than a nicety: see
[the user agent trap](#the-user-agent-trap).

---

## Build

```batch
build.bat
```

Icon generation, then PyInstaller, then Inno Setup. About two minutes.

Two things to know before automating any of it:

- **`build.bat` ends in `pause`.** It will hang forever in a non-interactive shell. To run
  the steps directly:

  ```bash
  python assets\make_icon.py
  pyinstaller voice-transcriber.spec --clean --noconfirm
  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
  ```

- **`make_icon.py` raises `UnicodeEncodeError`** printing its success line to a cp1252
  console. The icon is written anyway. `set PYTHONIOENCODING=utf-8` silences it. A build
  that succeeded but looks failed is worse than a noisy one.

Output:

| Artifact | Size | What it is |
|---|---|---|
| `dist\Clembot-dictate\Clembot-dictate.exe` | ~283 MB unpacked | Portable folder, no Python needed |
| `dist\Clembot-dictate-Setup-<version>.exe` | ~74 MiB | The installer you distribute |

Check that a lazily imported module actually made it into the bundle, because it would go
missing quietly:

```bash
grep -c voice_command build/voice-transcriber/Analysis-00.toc
```

---

## Releasing

### Where the binary can live

The installer is about **74 MiB**. That rules out some hosts outright: Cloudflare Pages,
for instance, caps a single asset at **25 MiB**, so a Pages site can serve the small JSON
manifest but not the download it points at. Object storage (R2, S3) or GitHub Releases
both work. GitHub Releases has the side benefit of building the download reputation that
reduces SmartScreen friction over time.

### Order of operations

The manifest is the trigger. Publish it early and every existing install gets an update
banner pointing at a download that does not exist yet.

1. `python tools/check_release.py`
2. Upload the installer. **Fetch the URL back** and confirm it serves the bytes rather
   than an HTML error or a login page.
3. Submit to VirusTotal. PyInstaller bundles are flagged on first appearance routinely;
   if vendors flag it, file false-positive reports and expect three to five business days.
4. Publish or update the download page, including the SmartScreen instructions.
5. **Last:** publish `version.json` with the new `latest`, the real download `url`, and one
   sentence of `notes`.
6. `python tools/check_release.py --endpoint` and expect a clean pass. It is now checking
   exactly what a user's copy will see.

### Rollback

Serve the previous `latest` and leave the old installer up. There is no downgrade path
inside the app: the banner is informational and installs nothing. A bad release is fixed
forward.

---

## The user agent trap

Worth its own section, because it cost this project a feature that appeared to work for
months.

`updater.py` used to call `urllib.request.urlopen(url)` with no headers. Python's default
`User-Agent: Python-urllib/3.x` is rejected by Cloudflare's managed rules, which returned
**403 on every path of the host**, the homepage included. The updater catches every
exception and logs at debug level, by design, so nothing surfaced. The check had never
succeeded and would have kept failing after the manifest was hosted.

Measured against the same URL: `403` with the default agent, `200` with **any** named
agent, including plain `curl/8.0.1`. The fix is one header.

Three habits come out of it, and they generalise past this project:

- **Send a named user agent** from anything that calls home.
- **Probe with the shipping client**, not with a browser or curl. Opening the URL in a
  browser exercises a completely different client and proves nothing about the app. The
  preflight reads the agent string out of `updater.py` so the two cannot drift.
- **403 and 404 mean different things.** Blocked and absent look identical in a log line
  that only records "failed".

A `try/except` that swallows everything needs some way to see what it swallowed. That is
what `--endpoint` is.

---

## Installer behaviour

`installer.iss` keeps a fixed `AppId`, so a newer installer **upgrades in place** rather
than installing a second copy, and `CloseApplications=yes` shuts the running app down
first. That is what keeps PyInstaller's locked-DLL problem away from users.

Nothing that matters lives in the app folder. History, logs, settings, the startup
registry entry and the model cache all sit in `%APPDATA%` or the user profile, so they
survive an upgrade. The uninstaller removes the `Run` registry entry and *offers* to
delete `%APPDATA%\Clembot-dictate`; declining keeps your history for a reinstall.

---

## Testing a release

Automated coverage stops at the seams. **The GUI is not covered**, so run this by hand on
the built artifact, not on the source tree:

| # | Do this | Expect |
|---|---|---|
| 1 | Launch, wait for the header to settle | Tray icon present, status idle |
| 2 | Hold the hotkey in Notepad, speak, release | Text at the cursor, tray red while held |
| 3 | Hold and release inside 0.3 s | Nothing happens, no empty history entry |
| 4 | Hold Ctrl with the hotkey, with no sidecar running | Falls back to dictation. **Nothing pasted is a bug** |
| 5 | Rebind the hotkey in Settings, use the new key | Works with no restart |
| 6 | Toggle Clipboard-only, dictate | Text on the clipboard, no paste, badge in the header |
| 7 | Disconnect the microphone, hold the hotkey | A clear failure, not a crash |
| 8 | Stop Ollama, dictate with cleanup on | Raw transcript pasted, nothing lost |

Steps 4, 7 and 8 are the degraded paths. They are the ones people skip and the ones most
likely to be broken.

Then test the release rather than the build: on a machine that has never seen the app,
download from the real URL, install, launch, and confirm the About box shows the new
version. A build verified only on the machine that built it proves that the compiler works.
