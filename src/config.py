import os
from pathlib import Path

VERSION = "1.2.1"

# Clembot-dictate — Configuration
# Edit these values to customize behavior. Restart required for changes to take effect.

# Minimum held duration (seconds) to trigger transcription.
# Taps shorter than this are silently discarded — prevents accidental hotkey fires.
MIN_RECORD_SECS = 0.3

# Global hotkey that triggers recording while held.
HOTKEY = "`"

# faster-whisper model size.
# "tiny"  — fastest, lower accuracy (~75MB)
# "small" — slower on this machine (benchmarked Phase 0)
MODEL_SIZE = "tiny"

# ---------------------------------------------------------------------------
# Auto-update
# ---------------------------------------------------------------------------
# URL of a JSON file with: { "latest": "1.1.0", "url": "...", "notes": "..." }
# Set to "" to disable the check entirely.
UPDATE_CHECK_URL = "https://wanessalabs.com/clembot-dictate/version.json"

# SHA256 of model.bin for integrity verification.
# Run tools/get_model_hash.py after first launch to get the value, then paste it here.
# None = skip the check (safe default until you've verified your own download).
MODEL_SHA256: str | None = None

# Audio input device index. None = system default microphone.
# To list devices: python -c "import sounddevice; print(sounddevice.query_devices())"
AUDIO_DEVICE = None

# Audio sample rate. 16000 Hz is what Whisper expects — do not change.
SAMPLE_RATE = 16000

# Channels. Mono only — Whisper does not use stereo.
CHANNELS = 1

# Optional audio cues. True = play a short beep on record start and stop.
AUDIO_CUES = True

# ---------------------------------------------------------------------------
# Output normalisation
# ---------------------------------------------------------------------------

# Strip invisible characters (zero-width spaces, word joiners) and normalise
# exotic spaces (NBSP, narrow NBSP) from text before it is pasted. LLM
# refinement emits these; they land invisibly wherever you were typing.
# Output hygiene only: it does not touch statistical watermarks and proves
# nothing about authorship. See src/vendor/ATTRIBUTION.md.
NORMALIZE_OUTPUT = True

# Tap Shift + the hotkey to run that same normalisation over whatever is on the
# clipboard, in place. Also available from the tray menu. Needs no model and no
# network, so it works while Whisper is still loading.
#
# Layer A only: invisible characters and exotic spaces. It does NOT remove em
# dashes, curly quotes or ellipses. Those are visible, legitimate characters,
# and house style is a separate decision this app does not make for you. Set
# False to disable the Shift branch and hide the tray item.
CLIPBOARD_CLEAN_ENABLED = True

# ---------------------------------------------------------------------------
# LLM Refinement
# ---------------------------------------------------------------------------

REFINE_WITH_AI = True

# Backend: "ollama" (local, free) or "anthropic" (Claude API, requires key)
REFINE_BACKEND = "ollama"

# ---------------------------------------------------------------------------
# Ollama settings
# ---------------------------------------------------------------------------
OLLAMA_MODEL = "gemma3:4b"
OLLAMA_HOST  = "http://localhost:11434"

# Refinement sits between the transcript and the paste, so a slow call is a slow
# paste. Measured 2026-08-20 on a loaded machine: a cold gemma3:4b took 102 s to
# return eight tokens, because llama-server had crashed and the 3.3 GB model was
# reloading under memory pressure. With no timeout the app simply waited.
# Past this, the raw transcript is pasted instead. Words late are worse than words
# unpolished.
OLLAMA_TIMEOUT = 25

# Keep the model resident between dictations. Ollama's default unloads after 5
# minutes idle, which makes every dictation after a coffee break pay the reload.
# Set to "0" to unload immediately if you would rather have the RAM back.
OLLAMA_KEEP_ALIVE = "30m"

# ---------------------------------------------------------------------------
# Anthropic settings
# ---------------------------------------------------------------------------
# Requires: setx ANTHROPIC_API_KEY "sk-ant-..."
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

# ---------------------------------------------------------------------------
# Voice commands (optional sidecar)
# ---------------------------------------------------------------------------
# Hold Ctrl while pressing the hotkey to ask a question instead of dictating.
# The answer is spoken by the voice-loop sidecar, which runs as a separate
# process with its own dependencies — nothing here changes dictation.
#
# Set to False to disable the Ctrl branch entirely. When the sidecar is not
# running, a Ctrl-held utterance falls back to ordinary dictation.
VOICE_COMMAND_ENABLED = True

# Written by the sidecar on startup: host, port, token, pid. User-level, so this
# carries no assumption about where anyone keeps their projects.
VOICE_COMMAND_STATE = (
    Path(os.environ.get("LOCALAPPDATA") or (Path.home() / ".local" / "state"))
    / "voice-loop" / "sidecar.json")

# Generous: a tier-3 answer measured up to 95 s on a tool-heavy question.
VOICE_COMMAND_TIMEOUT = 120

# ---------------------------------------------------------------------------
# Session Context File
# ---------------------------------------------------------------------------
# Optional plain-text file with notes on what you're working on.
# Read on every call — update mid-session, no restart needed.
# Create: mkdir %USERPROFILE%\.clembot && echo your notes > %USERPROFILE%\.clembot\context.txt
CONTEXT_FILE = Path("~/.clembot/context.txt").expanduser()

# ---------------------------------------------------------------------------
# Context Modes
# ---------------------------------------------------------------------------
# Each mode has a system prompt that shapes how the AI interprets your voice.
# Selected at runtime via the UI dropdown — no restart needed.
# Add new modes here and they will appear automatically in the dropdown.

CONTEXT_MODES = {
    "Claude Code": """\
You are a developer command optimizer. You receive raw voice dictation \
from a developer and convert it into a precise, actionable terminal \
command or prompt.

Rules:
- Remove filler words, false starts, and repetition
- Infer developer intent from context clues in the dictation
- Preserve technical terms exactly as spoken: hook, subagent, CLAUDE.md, diff, commit, branch, etc.
- Output ONLY the optimized command or prompt — no explanation, no preamble
- If the input is a question, format it as a direct question
- If the input is an instruction, format it as an imperative command""",

    "Work writing": """\
You are a professional writing assistant. You receive raw voice dictation \
and convert it into clear, polished written communication.

Rules:
- Remove filler words, false starts, and repetition
- Correct grammar and improve clarity without changing the speaker's meaning
- Match the appropriate register: casual for messages, formal for emails or documents
- Preserve the speaker's voice — do not over-polish or make it sound generic
- Output ONLY the refined text — no explanation, no labels, no meta-commentary""",
}

# The mode selected on startup. Must match a key in CONTEXT_MODES exactly.
DEFAULT_CONTEXT_MODE = "Claude Code"

# ---------------------------------------------------------------------------
# Auto-context from active window
# ---------------------------------------------------------------------------
# When True, Clembot-dictate detects the foreground window at hotkey press
# and auto-selects the matching context mode from WINDOW_MAP.
# Requires: pip install pywin32 psutil
AUTO_CONTEXT = True

# Map process names (lowercase) → context mode keys (must match CONTEXT_MODES).
WINDOW_MAP = {
    "code.exe":              "Claude Code",
    "windowsterminal.exe":   "Claude Code",
    "cmd.exe":               "Claude Code",
    "powershell.exe":        "Claude Code",
    "python.exe":            "Claude Code",
    "cursor.exe":            "Claude Code",
    "obsidian.exe":          "Work writing",
    "chrome.exe":            "Work writing",
    "firefox.exe":           "Work writing",
    "msedge.exe":            "Work writing",
    "outlook.exe":           "Work writing",
    "winword.exe":           "Work writing",
    "notepad.exe":           "Work writing",
    "notepad++.exe":         "Work writing",
    "slack.exe":             "Work writing",
    "teams.exe":             "Work writing",
}

# Fallback mode if the active window's process isn't in WINDOW_MAP.
AUTO_CONTEXT_FALLBACK = "Claude Code"
