"""
Voice Transcriber — main entry point (GUI mode).

Architecture:
  Main thread  → tkinter (HistoryWindow.mainloop)
  Thread: keys → keyboard listener (hold hotkey = record)
  Thread: tray → pystray (run_detached)
  Thread: load → model loading on startup (daemon)
  Thread: work → per-dictation transcribe + paste (daemon)
  Thread: work → per-card Run AI (daemon, on demand)
"""

import ctypes
import os
import sys
import threading
import time
from pathlib import Path

import keyboard

from logger import get_logger
from config import (CLIPBOARD_CLEAN_ENABLED, HOTKEY, MIN_RECORD_SECS, NORMALIZE_OUTPUT,
                    REFINE_WITH_AI, REFINE_BACKEND, VOICE_COMMAND_ENABLED)
from window_detector import get_context_for_active_window
from cues import play_start, play_stop
from recorder import Recorder
from transcriber import Transcriber
from refiner import Refiner
import paster
from paster import paste
import normalizer
from history import History, Entry
from tray import TrayIcon
from ui import HistoryWindow
from updater import check_for_update
import voice_command


log = get_logger("main")

_LOG_PATH = (
    Path.home() / "AppData" / "Roaming" / "Clembot-dictate" / "logs" / "clembot-dictate.log"
)

# Written on first successful launch so the balloon only fires once.
_FIRST_RUN_FLAG = Path.home() / "AppData" / "Roaming" / "Clembot-dictate" / ".first_run_done"


# ---------------------------------------------------------------------------
# Single-instance guard
# ---------------------------------------------------------------------------

_MUTEX = None


def _ensure_single_instance():
    global _MUTEX
    ERROR_ALREADY_EXISTS = 183
    _MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\ClemBotDictate_c7f3a2b9")
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        ctypes.windll.user32.MessageBoxW(
            0,
            "Clembot-dictate is already running.\nCheck the system tray.",
            "Clembot-dictate",
            0x40,
        )
        sys.exit(0)


# ---------------------------------------------------------------------------
# Crash handlers
# ---------------------------------------------------------------------------

def _show_crash_dialog(exc_value: BaseException):
    ctypes.windll.user32.MessageBoxW(
        0,
        f"An unexpected error occurred:\n\n{exc_value}\n\nFull details in:\n{_LOG_PATH}",
        "Clembot-dictate — Fatal Error",
        0x10,
    )


def _handle_uncaught(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, SystemExit):
        return
    log.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    _show_crash_dialog(exc_value)


def _handle_thread_crash(args):
    if args.exc_type is SystemExit:
        return
    log.critical("Unhandled thread exception", exc_info=(args.exc_type, args.exc_value, args.exc_tb))
    _show_crash_dialog(args.exc_value)


# ---------------------------------------------------------------------------
# First-launch detection
# ---------------------------------------------------------------------------

def _is_first_launch() -> bool:
    return not _FIRST_RUN_FLAG.exists()


def _mark_launched():
    try:
        _FIRST_RUN_FLAG.touch()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Shared state
# History is init'd synchronously (HistoryWindow needs it at construction).
# Recorder / Transcriber / Refiner are init'd in _load_models() so the UI
# appears immediately and shows progress during the model download.
# ---------------------------------------------------------------------------

_history:     History | None     = None
_recorder:    Recorder | None    = None
_transcriber: Transcriber | None = None
_refiner:     Refiner | None     = None
_model_ready  = False

_is_recording  = False
_record_start: float | None = None
_command_utterance = False        # set at key-down, read on release
_clean_utterance   = False        # ditto, for the Shift branch
_lock          = threading.Lock()

_press_hook   = None
_release_hook = None

_ui:  HistoryWindow | None = None
_tray: TrayIcon | None = None


# ---------------------------------------------------------------------------
# Model loading — background thread
# ---------------------------------------------------------------------------

def _load_models():
    global _recorder, _transcriber, _refiner, _model_ready

    try:
        # ── Mic permission check ────────────────────────────────────
        if not Recorder.check_mic_access():
            if _ui:
                _ui.set_status("● No mic", color="#f38ba8")
            result = ctypes.windll.user32.MessageBoxW(
                0,
                (
                    "Microphone access is blocked or no microphone was found.\n\n"
                    "Click Yes to open Windows microphone settings.\n"
                    "After granting access, restart Clembot-dictate."
                ),
                "Clembot-dictate — Microphone Required",
                0x24,  # MB_YESNO | MB_ICONWARNING
            )
            if result == 6:  # IDYES
                os.startfile("ms-settings:privacy-microphone")
            # Continue loading — history and AI features still work without mic.
            log.warning("Proceeding without mic access — dictation disabled.")

        # ── Model download / load ───────────────────────────────────
        cached = Transcriber.is_cached()
        status_text = "● Loading..." if cached else "● Downloading..."
        log.info("%s Whisper model...", "Loading" if cached else "Downloading")
        if _ui:
            _ui.set_status(status_text)

        _recorder    = Recorder()
        _transcriber = Transcriber()
        _refiner     = Refiner()
        _model_ready = True

        log.info("Model ready. Hold [%s] to dictate.", HOTKEY)
        if _ui:
            _ui.set_status(None)  # Restore "● Ready"

        # Warn if AI was requested but failed to initialize
        if REFINE_WITH_AI and not _refiner.is_enabled:
            msg = (
                "AI unavailable — Ollama not running. Run: ollama serve"
                if REFINE_BACKEND == "ollama"
                else "AI unavailable — check your API key in Settings → AI Key"
            )
            log.warning(msg)
            if _ui:
                _ui.set_status("⚠ AI offline", color="#f9e2af")
                threading.Timer(6.0, lambda: _ui.set_status(None)).start()
            if _tray:
                _tray.notify(msg)

        # ── First-launch balloon ────────────────────────────────────
        if _is_first_launch() and _tray:
            _tray.notify(f"Hold [{HOTKEY}] anywhere to dictate. Right-click this icon for options.")
            _mark_launched()

        # ── Version check ───────────────────────────────────────────
        def _on_update(latest, url, notes):
            if _ui:
                _ui.show_update_banner(latest, url)

        check_for_update(_on_update)

    except Exception as e:
        log.critical("Model loading failed: %s", e, exc_info=True)
        _show_crash_dialog(e)


# ---------------------------------------------------------------------------
# Hotkey handlers  (keyboard thread)
# ---------------------------------------------------------------------------

def _on_press(_event):
    global _is_recording, _record_start, _command_utterance, _clean_utterance

    # Shift makes this a clipboard clean rather than a dictation. Checked before
    # the model-ready guard on purpose: cleaning needs no model, so it works
    # during the first-launch download. Shift wins over Ctrl.
    if CLIPBOARD_CLEAN_ENABLED and keyboard.is_pressed("shift"):
        with _lock:
            if _is_recording:
                return
            _clean_utterance = True
        return

    if not _model_ready:
        return
    with _lock:
        if _is_recording:
            return
        _is_recording = True
        _record_start = time.monotonic()
        # Ctrl held at press time makes THIS utterance a question for the voice
        # sidecar rather than dictation. Per-utterance, so there is no mode to
        # switch and none to forget. Plain hotkey behaviour is unchanged.
        _command_utterance = VOICE_COMMAND_ENABLED and keyboard.is_pressed("ctrl")
    detected_mode = get_context_for_active_window()
    if detected_mode and _ui:
        _ui.set_context_mode(detected_mode)
    play_start()
    if not _recorder.start():
        with _lock:
            _is_recording = False
        if _tray:
            _tray.notify("Microphone unavailable — check your audio device.")
        return
    if _ui:   _ui.set_recording(True)
    if _tray: _tray.set_recording(True)


def _on_release(_event):
    global _is_recording, _record_start, _clean_utterance

    with _lock:
        pending_clean, _clean_utterance = _clean_utterance, False
    if pending_clean:
        threading.Thread(target=_clean_clipboard, daemon=True).start()
        return

    if not _model_ready:
        return
    with _lock:
        if not _is_recording:
            return
        _is_recording = False
        duration = time.monotonic() - (_record_start or 0)

    if _ui:   _ui.set_recording(False)
    if _tray: _tray.set_recording(False)

    # Discard accidental taps below the minimum duration threshold.
    if duration < MIN_RECORD_SECS:
        log.debug("Tap too short (%.3fs) — discarding.", duration)
        _recorder.stop()  # Drain the buffer without transcribing
        return

    play_stop()
    threading.Thread(target=_transcribe_and_paste, daemon=True).start()


def _ask_voice_command(audio) -> bool:
    """Send the utterance to the voice-loop sidecar. True when it answered.

    Raw audio rather than our transcript: the sidecar runs a larger Whisper model
    (base vs our tiny), measured 5 of 5 correct on spoken commands against 3 of 5.

    Every failure returns False so the caller falls through to ordinary dictation.
    A missing sidecar must never cost the user their words.
    """
    try:
        reply = voice_command.ask(audio)
    except Exception as e:                      # the client is stdlib, but never trust
        log.error("Voice command client error: %s", e)
        return False

    if not reply.ok:
        log.info("Voice command unavailable (%s) — dictating instead.", reply.error)
        if _tray:
            _tray.notify(f"Voice command unavailable: {reply.error}")
        return False

    log.info("Voice command [tier %s/%s]: %r", reply.tier, reply.intent, reply.speech)
    entry = _history.add(text=reply.speech, raw="[voice command]")
    if _ui:
        _ui.add_entry(entry)
    return True                                  # the sidecar speaks; nothing is pasted


def _transcribe_and_paste():
    if not _model_ready or _recorder is None or _transcriber is None:
        return

    audio = _recorder.stop()
    if audio is None:
        return

    if _command_utterance and _ask_voice_command(audio):
        return

    try:
        raw = _transcriber.transcribe(audio)
        if not raw:
            log.info("No speech detected.")
            return

        if _ui and _ui.ai_enabled:
            text = _refiner.refine(raw, mode=_ui.context_mode)
        else:
            text = raw

        # Nothing reaches the clipboard un-normalised, refined or not. Never
        # raises: on any failure it returns the text unchanged.
        if NORMALIZE_OUTPUT:
            text, _norm = normalizer.normalize(text)
            if _norm["removed"] or _norm["replaced"]:
                log.info("Normalised output: removed=%d replaced=%d",
                         _norm["removed"], _norm["replaced"])

        log.info("Final: %r", text)
        entry = _history.add(text=text, raw=raw)
        if _ui:
            _ui.add_entry(entry)
        paste(text, clipboard_only=_tray.clipboard_only if _tray else False)

    except Exception as e:
        log.error("Transcribe/paste error: %s", e)


# ---------------------------------------------------------------------------
# Run AI callback
# ---------------------------------------------------------------------------

def _on_run_ai(raw: str, entry: Entry, done_cb):
    if not _model_ready or _refiner is None:
        done_cb(raw)
        return

    mode = _ui.context_mode if _ui else None

    def worker():
        try:
            refined = _refiner.refine(raw, mode=mode)
            if NORMALIZE_OUTPUT:
                refined, _ = normalizer.normalize(refined)
            _history.update_text(entry, refined)
            done_cb(refined)
        except Exception as e:
            log.error("Run AI error: %s", e)
            done_cb(raw)

    threading.Thread(target=worker, daemon=True).start()


# ---------------------------------------------------------------------------
# Clipboard hygiene
# ---------------------------------------------------------------------------

def _clean_clipboard():
    """Normalise whatever is on the clipboard, in place.

    The same Layer A pass dictation output already gets: invisible characters
    and exotic spaces. Em dashes, curly quotes and ellipses survive on purpose.
    They are visible, legitimate characters, and removing them is a house-style
    decision this app does not make for you.

    Every decision lives in normalizer.plan_clipboard_clean, which is pure and
    tested. This function is the I/O around it, and it writes back only a
    strict improvement: on any other outcome the original is left untouched.
    """
    replacement, message = normalizer.plan_clipboard_clean(paster.read_clipboard())

    if replacement is not None:
        try:
            paste(replacement, clipboard_only=True)
        except Exception as e:
            log.error("Clipboard clean: write-back failed: %s", e)
            message = "Could not write the cleaned text back to the clipboard."

    log.info("Clipboard clean: %s", message)
    if _tray:
        _tray.notify(message)


def _request_clean():
    """Tray-menu entry point. Off the pystray thread, which must not block."""
    threading.Thread(target=_clean_clipboard, daemon=True).start()


# ---------------------------------------------------------------------------
# Keyboard listener
# ---------------------------------------------------------------------------

def _on_rebind(new_key: str) -> bool:
    global _press_hook, _release_hook
    try:
        if _press_hook:
            keyboard.unhook(_press_hook)
        if _release_hook:
            keyboard.unhook(_release_hook)
        _press_hook   = keyboard.on_press_key(new_key, _on_press, suppress=True)
        _release_hook = keyboard.on_release_key(new_key, _on_release, suppress=True)
        log.info("Hotkey rebound to %r", new_key)
        return True
    except Exception as e:
        log.error("Rebind failed: %s", e)
        return False


def _start_keyboard_listener():
    global _press_hook, _release_hook
    _press_hook   = keyboard.on_press_key(HOTKEY, _on_press, suppress=True)
    _release_hook = keyboard.on_release_key(HOTKEY, _on_release, suppress=True)
    keyboard.wait()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    _ensure_single_instance()

    sys.excepthook = _handle_uncaught
    threading.excepthook = _handle_thread_crash

    global _history, _ui, _tray

    # History is lightweight (reads JSON) — init synchronously before UI.
    _history = History()

    _ui   = HistoryWindow(_history, on_run_ai=_on_run_ai, on_rebind=_on_rebind)

    def _on_clipboard_change(active: bool):
        if _ui:
            _ui.set_clipboard_only(active)

    _tray = TrayIcon(
        on_show=_ui.show,
        on_quit=_quit,
        on_clipboard_toggle=_on_clipboard_change,
        on_clean=_request_clean if CLIPBOARD_CLEAN_ENABLED else None,
    )

    threading.Thread(target=_start_keyboard_listener, daemon=True).start()
    _tray.run_detached()

    # Model loads in background — UI appears immediately showing progress.
    threading.Thread(target=_load_models, daemon=True).start()

    log.info("UI ready. Model loading in background.")

    _ui.show_passive()
    _ui.mainloop()


def _quit():
    if _tray:
        _tray.stop()
    if _ui:
        _ui.quit()
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
    except Exception as e:
        log.critical("Fatal startup error", exc_info=True)
        _show_crash_dialog(e)
