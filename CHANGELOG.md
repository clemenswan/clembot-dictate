# Changelog

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
