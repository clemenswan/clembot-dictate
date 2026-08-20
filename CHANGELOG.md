# Changelog

## 1.1.1

An interface pass.

**The window lost its title bar.** A 44px strip was carrying 32px of chrome whose
minimise and maximise buttons meant nothing for a tray tool. It is frameless now, drag
it by the bar, and it stays on top since it no longer has a taskbar entry.

**A palette of its own.** The interface was painted in Catppuccin Mocha, a third-party
developer theme, in sixteen hardcoded colours. It now derives a warm dark palette with a
forest green accent from the Wanessa Labs system, in one file. Every text colour was
measured against its background; the lowest ratio in the app is 5.1:1.

**Icons instead of emoji.** The header was built from `●`, `▼`, `⚙`, `⟳`, `📋` and `✕`,
which take the system emoji font's colour rather than the app's and cannot be sized to a
grid. They are drawn now, at one stroke weight.

**History cards fit their contents.** Every entry was padded to three lines regardless of
length, so a full panel showed one and a half of them. A card built before the panel was
open had no width yet, so a one-line transcript measured as three and stayed that way.
Fixed, and two entries now fit where one and a half did.

**Type has a scale**: four sizes, one family, state words set as spaced uppercase labels.
Previously four sizes at three weights with nothing behind the choice.

The tray icon is on the palette too, green when idle rather than slate.

## 1.1.0

**Voice commands (optional).** Hold Ctrl with the hotkey and the utterance becomes a
spoken question instead of pasted text, answered by a local sidecar process. Ctrl is
sampled at key-down, so it is per utterance rather than a mode. With no sidecar running
the utterance falls back to ordinary dictation and the tray says why, so the feature is
dormant rather than broken. The sidecar itself is not published yet.

**Fixed: the update check could never have worked.** It sent Python's default
`urllib` user agent, which Cloudflare's managed rules reject on every path of the host
serving the version manifest, and the check swallows exceptions by design. It had failed
silently since it was written. It now sends a named agent.

**Added `tools/check_release.py`.** Compares every file that names a version, checks the
installer exists, and probes the update endpoint using the agent read out of `updater.py`,
because checking with a different client than the app uses proves nothing about the app.
Written after three files shipped a release still naming the previous version.

## 1.0.0

First public build.

- Hold-to-speak, release-to-paste, in any Windows app
- Local transcription with faster-whisper, in memory, no temporary files
- Optional text cleanup with Ollama (local) or Claude (cloud)
- Context modes selected automatically from the foreground window
- History with the raw transcript and the cleaned version side by side
- System tray, live hotkey rebinding, clipboard-only mode
- Single-instance guard, crash handlers, rotating log, microphone permission check
- Inno Setup installer, no admin rights, upgrades in place
