# Clembot-dictate

Hold a key. Speak. Release. Your words appear wherever your cursor is, in any Windows app.

No window to click. No app switching. No cloud. No subscription. Transcription runs on
your own CPU, and your audio never leaves the machine.

```
hold `  →  speak  →  release  →  text at your cursor
```

Built by [Wanessa Labs](https://wanessalabs.com). MIT licensed.

---

## Contents

- [Why this exists](#why-this-exists)
- [Install](#install)
- [Usage](#usage)
- [Configuration](#configuration)
- [Context modes](#context-modes)
- [Voice commands](#voice-commands)
- [How it works](#how-it-works)
- [Build it yourself](#build-it-yourself)
- [Troubleshooting](#troubleshooting)
- [Privacy](#privacy)
- [Project layout](#project-layout)

---

## Why this exists

Windows dictation is poor for people who type all day.

**Windows Voice Typing** needs activating for every session and does not behave the same
way in every app. **Dragon** costs hundreds a year and sends audio to a server. **Other
Whisper desktop tools** still make you interact: open a window, click record, click stop,
copy, switch back, paste. That is five steps for something that should be none.

This is none. The whole interaction is a held key, so it disappears into your typing the
way a keyboard shortcut does.

| | Clembot-dictate | Windows Voice Typing | Dragon | Typical Whisper apps |
|---|---|---|---|---|
| Zero-interaction gesture | Yes | No | No | No |
| Works in any Windows app | Yes | Partial | Yes | No |
| Fully local | Yes | No | No | Varies |
| Shapes text to the app you are in | Yes | No | Limited | No |
| Raw and cleaned text both kept | Yes | No | No | No |
| Cost | Free | Free | Paid | Varies |

---

## Install

### Requirements

- Windows 10 or 11
- A microphone
- Python 3.10+ (only if running from source)
- Optional: [Ollama](https://ollama.com) for free local text cleanup
- Optional: an Anthropic API key for cloud text cleanup

### Option A: Windows installer

Download the latest `Clembot-dictate-Setup-<version>.exe` from
[Releases](https://github.com/clemenswan/clembot-dictate/releases).

> **No binary is published yet.** The 1.1.0 installer is built and in use, but it has not
> been attached to a release here. Until it is, [Option B](#option-b-from-source) is the
> way in. Watch the repo if you would rather wait for the installer.

1. Run it. It installs to `%LOCALAPPDATA%\Programs\Clembot-dictate`, no admin rights.
2. Windows shows **"Windows protected your PC"** because the binary is unsigned. Click
   **More info**, then **Run anyway**. Once per machine.
3. Launch from the Start Menu. It lives in the system tray.

The speech model (about 75 MB) downloads on first launch and is cached in
`%USERPROFILE%\.cache\huggingface\hub`.

> **On the SmartScreen warning.** Code signing certificates cost money this project does
> not spend yet. If that is a dealbreaker, run from source instead: it is the same code.

### Option B: From source

```bash
git clone https://github.com/clemenswan/clembot-dictate.git
cd clembot-dictate
pip install -r requirements.txt
python src/main.py
```

Optional local cleanup model:

```bash
ollama pull gemma3:4b
```

Full developer setup, including every configuration knob: [docs/setup.md](docs/setup.md).

---

## Usage

| Do this | Get this |
|---|---|
| Hold backtick, speak, release | Text pasted at your cursor |
| Hold Ctrl + backtick, speak, release | A spoken answer instead of text ([see below](#voice-commands)) |
| Click the tray icon | Open the history panel |
| Toggle **AI** in the header | Turn text cleanup on or off for the next dictation |
| Click **Run AI** on a history card | Re-clean an earlier dictation in a different mode |
| Right-click tray → **Clipboard only** | Copy instead of pasting, for elevated windows and RDP |
| Settings → **Hotkey** | Rebind the key. Takes effect immediately, no restart |
| Settings → **AI Key** | Store an Anthropic key in Windows Credential Manager |

A 52 px header strip sits at the top of the screen showing state. The history panel slides
out when you want it and stays out of the way when you do not. The tray icon turns red
while recording.

Taps shorter than 0.3 s are discarded, so brushing the key does not create an empty entry.

---

## Configuration

Everything lives in `src/config.py` as plain module constants. No config format to learn.

```python
HOTKEY          = '`'        # any key or combination
MODEL_SIZE      = 'tiny'     # 'tiny' (75 MB, <3 s) | 'small' (240 MB) | 'medium'
AUDIO_DEVICE    = None       # None = system default microphone
AUDIO_CUES      = True       # beep on start and stop
MIN_RECORD_SECS = 0.3        # shorter holds are ignored

REFINE_WITH_AI  = True
REFINE_BACKEND  = 'ollama'   # 'ollama' (local, free) or 'anthropic' (cloud)
OLLAMA_MODEL    = 'gemma3:4b'
ANTHROPIC_MODEL = 'claude-haiku-4-5-20251001'

UPDATE_CHECK_URL = 'https://wanessalabs.com/clembot-dictate/version.json'
```

Two notes for anyone running a fork:

- **`UPDATE_CHECK_URL` points at the original project.** It is a single GET at startup
  that reads a version number. Set it to `""` to disable the check entirely, or point it
  at your own JSON.
- **API keys are never written to disk by this app.** The key you enter in Settings goes
  to Windows Credential Manager through `keyring`. The `ANTHROPIC_API_KEY` environment
  variable still works as a fallback.

Model, backend, and audio device changes need a restart. Hotkey and context file changes
do not.

---

## Context modes

Raw speech is messy, and how it should be cleaned depends on what you are doing. A mode
is a system prompt plus a list of apps it belongs to.

| Mode | Turns speech into | Activates in |
|---|---|---|
| Claude Code | Precise developer commands and prompts, technical terms preserved | VS Code, Windows Terminal, PowerShell, Cursor |
| Work writing | Clear written prose at the right register | Obsidian, Word, Outlook, browsers, Slack |

The active window is read **at the moment you press the key**, before recording starts, so
switching from your editor to your mail client switches the mode with no UI at all.

Add your own by editing one dict:

```python
CONTEXT_MODES = {
    'My mode': 'You are a...',
}

WINDOW_MAP = {
    'myapp.exe': 'My mode',
}
```

### Session context

Create `~/.clembot/context.txt` and write whatever the model should know: the project,
the vocabulary, the tone. It is re-read on every call, so you can edit it mid-session.

```
Project: acme-api
Stack: Go, Postgres, Kubernetes
Tone: direct and technical, no filler
```

---

## Voice commands

Hold **Ctrl together with the hotkey** and the same gesture asks a question instead of
typing one. The audio goes to a local sidecar process, which transcribes it, decides how
much machinery the question deserves, answers, and speaks the result. Nothing is pasted.

Ctrl is sampled once at key-down, so this is per utterance rather than a mode. There is
nothing to toggle and nothing to forget, which matters: a mode you forget you are in
pastes an answer into a document.

> **Status: the sidecar is not published yet.** The answering half is a separate project
> called voice-loop, which is not open source at the time of writing. Everything for it
> in this repository (`src/voice_command.py` and the Ctrl branch in `src/main.py`) is
> shipped and working, but with no sidecar running, **a Ctrl-held utterance falls back to
> ordinary dictation** and the tray says why. Nothing breaks; the feature is simply
> dormant. Watch this repo if you want it.

The design is worth describing even so, because the fallback behaviour is the part that
affects you:

- The sidecar publishes its host, port, token and process id to
  `%LOCALAPPDATA%\voice-loop\sidecar.json`.
- The client reads that file at Ctrl-down and checks the process is alive, so a stale file
  from a killed process reads as "not running" rather than hanging the app.
- Every failure path returns "not available" and falls through to dictation: missing file,
  dead port, unreachable socket, error payload, unparseable response. **A missing sidecar
  never costs you words.**
- Set `VOICE_COMMAND_ENABLED = False` in `src/config.py` to remove the branch entirely.

The client is deliberately **standard library only**. An optional feature is not allowed
to change what the installer has to carry.

---

## How it works

```
Keyboard thread              UI thread (customtkinter)      Tray thread (pystray)
      |                              |                             |
  hotkey press                       |                             |
      |---> read the active window                                 |
      |---> sample Ctrl: held = question, not dictation            |
      |---> start capture (sounddevice, straight into a buffer)    |
      |---> tray: recording = true -------------------------------->|
      |                                                            |
  hotkey release                                                   |
      |---> stop capture                                           |
      |---> tray: recording = false ------------------------------->|
      |
  Daemon thread (per utterance)
      |
      |-- Ctrl was held and a sidecar is up?
      |     |---> ask over 127.0.0.1, answer is spoken, nothing pasted
      |
      |-- otherwise
            |---> faster-whisper: audio array -> raw text
            |---> optional cleanup: raw text + mode + session context
            |---> history: raw and cleaned kept side by side
            |---> clipboard write -> synthesized Ctrl+V -> your cursor
```

**Audio never touches disk.** The buffer goes from the microphone into
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) with no temporary WAV in
between, which removes a file round trip from every dictation.

Everything after the key event runs off the main thread, so the hotkey listener never
blocks. All UI updates from background threads go through `root.after(0, fn)`, which is
the only safe way to touch tkinter from another thread.

### Stack

| Layer | Library |
|---|---|
| Transcription | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2, CPU, int8) |
| Audio capture | [sounddevice](https://python-sounddevice.readthedocs.io) |
| Global hotkey | [keyboard](https://github.com/boppreh/keyboard) |
| Text cleanup | [Ollama](https://ollama.com) or [Anthropic](https://anthropic.com) |
| UI | [customtkinter](https://github.com/TomSchimansky/CustomTkinter) |
| Tray | [pystray](https://github.com/moses-palmer/pystray) + [Pillow](https://python-pillow.org) |
| Paste | [pyperclip](https://github.com/asweigart/pyperclip) + [pyautogui](https://pyautogui.readthedocs.io) |
| Key storage | [keyring](https://github.com/jaraco/keyring) (Windows Credential Manager) |
| Window detection | pywin32 + psutil |

---

## Build it yourself

```batch
build.bat
```

Icon generation, then PyInstaller, then an [Inno Setup 6](https://jrsoftware.org/isinfo.php)
installer. Two minutes or so. Output:

- `dist\Clembot-dictate\Clembot-dictate.exe`, a portable folder that needs no Python
- `dist\Clembot-dictate-Setup-<version>.exe`, the installer

Before releasing anything, run the preflight. It compares every file that names a version,
checks the installer exists, and probes the update endpoint with the same user agent the
app itself sends:

```bash
python tools/check_release.py --endpoint
```

Full packaging and release notes, including the two constraints that bite:
[docs/building.md](docs/building.md).

---

## Troubleshooting

The short version:

| Symptom | Cause |
|---|---|
| Hotkey does nothing | An elevated window has focus, or another app holds the key |
| Nothing pastes | Some apps block synthetic Ctrl+V. The text is on your clipboard |
| Transcription is slow | Try a smaller model, or a machine with a GPU |
| "CUDA not available" at startup | Informational. CPU is the supported path |
| Ollama cleanup fails | Ollama is not running. The raw transcript is pasted, nothing is lost |
| Ctrl + hotkey dictates | No sidecar is running. Expected, see above |

Longer version, with log locations and how to read them:
[docs/troubleshooting.md](docs/troubleshooting.md).

---

## Privacy

- **Audio never leaves your machine and is never written to disk.** Capture, transcription
  and paste all happen in memory.
- **The optional cleanup pass is the only thing that can touch the network**, and only if
  you choose the cloud backend. With the default Ollama backend, nothing leaves the
  machine at all.
- **History is local**, at `%APPDATA%\Clembot-dictate\history.json`. Delete it whenever
  you like; the uninstaller offers to remove it for you.
- **No telemetry, no analytics, no account.** The only network call the app makes on its
  own is one version check at startup, which you can switch off.

---

## Project layout

```
src/
  main.py             entry point, startup, keyboard and model threads
  config.py           every setting, single source of truth
  recorder.py         microphone capture
  transcriber.py      faster-whisper wrapper, model cache and integrity check
  refiner.py          optional text cleanup (Ollama or Anthropic)
  paster.py           clipboard write, restore, synthesized Ctrl+V
  ui.py               header strip, history panel, settings
  tray.py             system tray icon
  history.py          JSON persistence
  logger.py           rotating log
  startup.py          launch-at-login registry entry
  updater.py          version check
  window_detector.py  active window to context mode
  cues.py             audio cues
  voice_command.py    sidecar client (standard library only)
assets/               icon generation
tools/                release preflight, model hash helper
docs/                 setup, building, troubleshooting
```

`src/hotkey_test.py`, `src/latency_test.py` and `src/paste_test.py` are small standalone
probes kept for diagnosing the three things that most often break on a new machine.

---

## Contributing

Issues and pull requests are welcome. Two things worth knowing before you open one:

- The app targets Windows. macOS and Linux support would need a different paste path and
  a different hotkey layer, and neither exists today.
- Please do not add a dependency to `src/voice_command.py`. Its standard-library-only
  constraint is load-bearing.

## License

MIT. See [LICENSE](LICENSE).
