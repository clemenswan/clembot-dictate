"""Client for the voice-loop sidecar. Stdlib only, by design.

Clembot-dictate must not grow voice-loop's dependencies. The loop needs
numpy >= 2.0.2 for kokoro-onnx and 354 MB of speech models; this app runs on
numpy 1.26.4 in a global environment and ships as a 283 MB installer. So the
two talk over a loopback socket and share nothing but JSON.

Everything here degrades: if the sidecar is missing, stale, or slow, `ask()`
returns `ok=False` and the caller falls back to ordinary dictation. A voice
command never blocks dictation from working.
"""

from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from pathlib import Path

from config import VOICE_COMMAND_STATE, VOICE_COMMAND_TIMEOUT


@dataclass(frozen=True)
class CommandReply:
    ok: bool
    speech: str = ""
    intent: str = ""
    tier: int = 0
    detail: str = ""
    error: str = ""


def read_state(path=None) -> dict | None:
    """Where the sidecar published its port and token, or None."""
    file = Path(path or VOICE_COMMAND_STATE).expanduser()
    if not file.is_file():
        return None
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not all(key in payload for key in ("host", "port", "token")):
        return None
    return payload


def ask(audio, path=None, timeout=None) -> CommandReply:
    """Send raw audio to the sidecar and return what it answered.

    Audio rather than a transcript on purpose: the sidecar runs a larger Whisper
    model than dictation does (base vs tiny), which measured 5 of 5 correct
    against 3 of 5 on spoken commands. A command that is misheard is useless;
    dictation can survive a wrong word.
    """
    state = read_state(path)
    if state is None:
        return CommandReply(False, error="sidecar not running")

    request = {
        "token": state["token"],
        "audio": [float(sample) for sample in audio],
        "rate": 16000,
    }
    try:
        with socket.create_connection((state["host"], int(state["port"])),
                                      timeout=timeout or VOICE_COMMAND_TIMEOUT) as sock:
            sock.sendall((json.dumps(request) + "\n").encode("utf-8"))
            buffer = b""
            while b"\n" not in buffer:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buffer += chunk
    except (OSError, socket.timeout) as exc:
        # A state file can outlive its process: on Windows a terminate() skips
        # the shutdown handler, so a stale file points at a dead port.
        return CommandReply(False, error=f"sidecar unreachable: {exc}")

    try:
        payload = json.loads(buffer.decode("utf-8").strip() or "{}")
    except json.JSONDecodeError as exc:
        return CommandReply(False, error=f"bad response: {exc}")

    if not payload.get("ok"):
        return CommandReply(False, error=str(payload.get("error", "unknown error")))
    return CommandReply(
        True,
        speech=payload.get("speech", ""),
        intent=payload.get("intent") or "",
        tier=int(payload.get("tier") or 0),
        detail=payload.get("detail", ""),
    )


def is_available(path=None) -> bool:
    """Cheap check for UI affordances. The socket is the truth, not the file."""
    state = read_state(path)
    if state is None:
        return False
    try:
        with socket.create_connection((state["host"], int(state["port"])), timeout=0.5):
            return True
    except OSError:
        return False
