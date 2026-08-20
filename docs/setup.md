# Setup, from source

For developers. If you only want to use the app, the installer in
[Releases](https://github.com/clemenswan/clembot-dictate/releases) is the shorter path.

---

## Prerequisites

- Windows 10 or 11
- Python 3.10 or newer
- A working microphone
- Optional: [Ollama](https://ollama.com), for free local text cleanup
- Optional: an Anthropic API key, for cloud text cleanup

---

## Install

```bash
git clone https://github.com/clemenswan/clembot-dictate.git
cd clembot-dictate
pip install -r requirements.txt
python src/main.py
```

On first launch the speech model (about 75 MB) downloads to
`%USERPROFILE%\.cache\huggingface\hub`. The header shows "● Downloading…" until it is
ready, then "● Loading…" on later starts while the model is read into memory.

If the microphone check fails, a dialog offers to open Windows Privacy Settings. Grant
access and restart.

A virtual environment is a good idea and not required:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuration

Everything is in `src/config.py`, as plain module constants. Restart is needed for model,
backend and audio device changes. Hotkey changes apply immediately through the UI, and
the session context file is re-read on every call.

### Hotkey

```python
HOTKEY = '`'
```

The key is captured with `suppress=True`, so the raw keystroke does not reach the app in
front while Clembot-dictate is running. Rebinding in Settings takes effect without a
restart, because the hook reference is kept and replaced rather than registered once.

### Transcription model

```python
MODEL_SIZE = 'tiny'   # 'tiny' (~75 MB, <3 s) | 'small' (~240 MB) | 'medium' (~750 MB)
```

Benchmark `tiny` on your own hardware before reaching for something larger. On a modern
CPU it handles about five seconds of speech inside the three second target. Accuracy
improves with size, and so does latency; a CUDA GPU changes the trade completely.

### Text cleanup

```python
REFINE_WITH_AI  = True
REFINE_BACKEND  = 'ollama'       # 'ollama' or 'anthropic'
OLLAMA_MODEL    = 'gemma3:4b'
ANTHROPIC_MODEL = 'claude-haiku-4-5-20251001'
```

**Ollama:** install it, pull the model, leave the server running. The model is warmed at
startup so the first dictation does not pay the cold start.

```bash
ollama pull gemma3:4b
ollama serve
```

**Anthropic:** add the key through Settings → AI Key, which stores it in Windows
Credential Manager through `keyring`. The `ANTHROPIC_API_KEY` environment variable works
as a fallback. The app never writes a key to a file.

If a cleanup call fails for any reason, the raw transcript is pasted instead. You never
lose the words.

### Update check

```python
UPDATE_CHECK_URL = 'https://wanessalabs.com/clembot-dictate/version.json'
```

One GET at startup, five second timeout, silent on failure, shows a dismissible banner if
a newer version exists. It never downloads or installs anything. Set it to `""` to
disable, or point it at your own manifest if you distribute a fork:

```json
{ "latest": "1.2.0", "url": "https://example.com/download", "notes": "One sentence." }
```

### Model integrity check

Optional. After the first successful download:

```bash
python tools/get_model_hash.py
```

Paste the printed value into `src/config.py`:

```python
MODEL_SHA256 = "abc123..."
```

`None` skips the check, which is the default and is fine for development.

---

## Where things live

| Path | Contents |
|---|---|
| `%APPDATA%\Clembot-dictate\history.json` | Dictation history, last 50 entries |
| `%APPDATA%\Clembot-dictate\logs\clembot-dictate.log` | Rotating log, 1 MB, 3 backups |
| `%APPDATA%\Clembot-dictate\.first_run_done` | Marker for the first-launch tray balloon |
| `%USERPROFILE%\.cache\huggingface\hub\` | Speech model cache |
| `~/.clembot/context.txt` | Optional session context, re-read on every call |
| `%LOCALAPPDATA%\voice-loop\sidecar.json` | Written by the voice command sidecar, if you run one |

**`history.json` holds what you actually said.** It is in `.gitignore` for that reason.
Check before you attach a log or a repository archive to a bug report.

---

## Development notes

**Threads.** The tkinter event loop owns the main thread. The keyboard listener, the tray,
model loading, each dictation, each on-demand cleanup, and the version check are all
daemon threads. Any UI update from one of them must go through `root.after(0, fn)`; calling
tkinter directly from another thread will fail in ways that look random.

**Standalone probes.** Three small scripts diagnose the things that break first on a new
machine, and each runs on its own:

```bash
python src/hotkey_test.py     # is the global hook firing at all
python src/paste_test.py      # does synthetic Ctrl+V reach the foreground app
python src/latency_test.py    # how long does transcription actually take here
```

**`src/voice_command.py` is standard library only, deliberately.** It is the client for
an optional sidecar, and an optional feature must not change what the installer carries.
Please keep it that way.

---

## Known limitations

| Issue | Where it bites | What to do |
|---|---|---|
| Auto-paste fails | Elevated windows, UAC, RDP, some locked-down apps | Turn on Clipboard-only in the tray and paste manually |
| Hotkey suppressed | UAC dialogs, DirectInput games | Rebind, or accept it in those contexts |
| SmartScreen warning | Any unsigned binary | More info → Run anyway, once per machine |
| Windows only | Everywhere else | The paste path and hotkey layer are Windows-specific |
