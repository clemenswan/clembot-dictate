# Troubleshooting

Where to look first, then the symptoms in rough order of how often they come up.

---

## Where the evidence is

| Path | What it holds |
|---|---|
| `%APPDATA%\Clembot-dictate\logs\clembot-dictate.log` | Rotating log, 1 MB, 3 backups |
| `%APPDATA%\Clembot-dictate\history.json` | Every dictation: raw transcript and cleaned version |
| `%LOCALAPPDATA%\voice-loop\sidecar.json` | Voice command sidecar host, port, token, pid |
| Console | `python src\main.py` from source puts tracebacks in front of you |

**`history.json` contains what you actually said.** Read it yourself, but scrub it before
attaching it to a bug report.

The single most useful habit: compare the **raw** transcript against what you meant to
say before blaming anything downstream. "It did the wrong thing" is very often "it heard
a different sentence", and those have completely different fixes.

---

## The hotkey does nothing

In order of likelihood:

1. **An elevated window has focus.** Global hooks do not reach UAC dialogs, an
   administrator terminal, or some anti-cheat protected games. Nothing to fix; use a
   different window.
2. **The model is still loading.** The hotkey is gated until it is ready. The header says
   "● Loading…" or "● Downloading…" while that is true.
3. **Another app owns the key.** Rebind in Settings; it applies immediately.
4. **The app is not actually running.** Check the tray, then Task Manager for
   `Clembot-dictate.exe`.

Confirm the hook itself in isolation:

```bash
python src/hotkey_test.py
```

---

## Nothing pastes, but the history entry exists

The transcription worked and the paste did not. Some applications refuse synthetic
`Ctrl+V`: Citrix, RDP sessions, certain IDEs and terminals with their own clipboard
handling.

The text is on your clipboard either way, so paste it manually. For anything where this
happens routinely, turn on **Clipboard only** in the tray menu; a `📋 clip` badge appears
in the header while it is active.

```bash
python src/paste_test.py     # isolates the paste path
```

---

## The app will not start

- **A previous instance is still alive.** A single-instance guard shows a dialog and exits
  rather than starting a second copy. Check Task Manager for `Clembot-dictate.exe`.
- **It crashed at startup.** Crash handlers cover the main thread and background threads,
  and show a dialog naming the log path. Read that log before anything else.
- **It was just upgraded.** The installer closes the running app first, but a wedged
  process can survive. Kill it and relaunch.

---

## Transcription is slow or inaccurate

Latency scales with model size and with how long you held the key. Measure rather than
guess:

```bash
python src/latency_test.py
```

- `tiny` handles about five seconds of speech within the three second target on a modern
  CPU.
- `small` and `medium` are more accurate and slower. Change `MODEL_SIZE` in
  `src/config.py` and restart.
- A CUDA GPU changes this substantially, on any model size.
- **"CUDA not available" at startup is informational.** CPU is the supported path.

Accuracy is usually a microphone problem before it is a model problem. Check the input
level in Windows sound settings, and set `AUDIO_DEVICE` explicitly if the default device
is not the one you think it is:

```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```

---

## Text cleanup does nothing, or makes it worse

- **Ollama is not running.** Start it (`ollama serve`) and confirm the model is pulled
  (`ollama list`). When the call fails, the raw transcript is pasted, so nothing is lost.
- **The wrong context mode is active.** The mode is chosen from the foreground window at
  the moment you press the key. An app that is not in `WINDOW_MAP` falls back to
  `AUTO_CONTEXT_FALLBACK`, which may not be what you want. Add the process name to the map.
- **The model is rewriting too much.** Edit the mode's prompt in `CONTEXT_MODES`, or turn
  cleanup off with the header toggle and keep the raw transcription.
- **The Anthropic backend does nothing.** No key is stored. Settings → AI Key, or set
  `ANTHROPIC_API_KEY`.

Every history card keeps both versions, so you can always see exactly what the model
changed.

---

## Ctrl + hotkey dictates instead of answering

Expected when no voice command sidecar is running. The Ctrl branch is optional and inert
without it, and the fallback is deliberate: a missing sidecar should never cost you words.

If you are running one and it is still falling back:

1. Does `%LOCALAPPDATA%\voice-loop\sidecar.json` exist?
2. Is the pid it names still alive? A stale file from a killed process is treated as
   "not running" rather than being trusted.
3. Is the port in that file actually accepting connections?

Set `VOICE_COMMAND_ENABLED = False` in `src/config.py` to remove the branch entirely.

---

## Something that calls the network silently does nothing

Worth knowing as a class of bug, because this project shipped one.

The update check sent Python's default `urllib` user agent, which the host's WAF rejected
with a 403 on every path. The check catches every exception and logs at debug level, so it
looked healthy while never once succeeding.

If a feature that calls out appears to do nothing:

- Reproduce the request **with the same client the app uses**, not with a browser and not
  with curl. They are different clients and they get different answers.
- Distinguish **403 from 404**. Blocked and absent look identical in a log line that only
  says "failed".
- Raise the log level and look at what the `except` actually caught.

```bash
python tools/check_release.py --endpoint
```

That probes the update endpoint using the agent read out of `src/updater.py`.

---

## Antivirus flags the download

PyInstaller bundles are flagged on first appearance routinely, because the packaging
pattern resembles what packers do. Nothing here is obfuscated and the source is in this
repository.

Options: run from source instead, submit a false-positive report to your vendor, or wait
for the detection to age out as the binary accumulates reputation.

---

## Filing a useful bug report

Include:

1. What you said, and what you got.
2. The raw transcript from the history entry, scrubbed if needed.
3. The matching window of `clembot-dictate.log`.
4. Whether cleanup was on, and which backend.
5. Windows version, and whether the target app was elevated.

Point 3 is the one people leave out, and it is usually the one with the answer in it.
