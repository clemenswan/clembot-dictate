"""
LLM refinement pass — cleans up raw Whisper transcripts.

Supports two backends (set REFINE_BACKEND in config.py):
  "ollama"    — local model via Ollama, free, no API key
  "anthropic" — Claude API, requires ANTHROPIC_API_KEY env var

Falls back to raw transcript if the backend is unavailable or errors.
"""

import os
import threading
import time

from logger import get_logger
from config import (
    REFINE_WITH_AI,
    REFINE_BACKEND,
    OLLAMA_MODEL,
    OLLAMA_HOST,
    OLLAMA_TIMEOUT,
    OLLAMA_KEEP_ALIVE,
    ANTHROPIC_MODEL,
    CONTEXT_FILE,
    CONTEXT_MODES,
    DEFAULT_CONTEXT_MODE,
)

log = get_logger("refiner")


class Refiner:
    def __init__(self):
        self._enabled = REFINE_WITH_AI
        self._backend = REFINE_BACKEND
        self._call = None

        if not self._enabled:
            return

        if self._backend == "ollama":
            self._call = self._setup_ollama()
            if self._call:
                threading.Thread(target=self._warmup, daemon=True).start()
        elif self._backend == "anthropic":
            self._call = self._setup_anthropic()
        else:
            log.warning("Unknown backend %r — disabled.", self._backend)
            self._enabled = False

    # ------------------------------------------------------------------
    # Context file + system prompt
    # ------------------------------------------------------------------

    def _get_context(self) -> str:
        """Read ~/.clembot/context.txt if it exists. Returns empty string on miss."""
        try:
            return CONTEXT_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            return ""

    def _build_system_prompt(self, mode: str | None = None) -> str:
        base = CONTEXT_MODES.get(mode or DEFAULT_CONTEXT_MODE, CONTEXT_MODES[DEFAULT_CONTEXT_MODE])
        context = self._get_context()
        if context:
            return f"{base}\n\nCurrent session context:\n{context}"
        return base

    # ------------------------------------------------------------------
    # Warm-up
    # ------------------------------------------------------------------

    def _warmup(self):
        """Send a silent dummy call so the model is resident before first dictation."""
        try:
            log.info("Warming up Ollama model...")
            self._call("ok")
            log.info("Ollama model warm.")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Backend setup
    # ------------------------------------------------------------------

    def _setup_ollama(self):
        try:
            import ollama
            client = ollama.Client(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT)
            models = [m.model for m in client.list().models]
            matched = next((m for m in models if m.startswith(OLLAMA_MODEL.split(":")[0])), None)
            if not matched:
                log.warning(
                    "Model %r not found in Ollama. Available: %s. Run: ollama pull %s. Falling back to raw.",
                    OLLAMA_MODEL, models, OLLAMA_MODEL,
                )
                self._enabled = False
                return None
            log.info("Ollama ready — model: %s", OLLAMA_MODEL)

            def call(text: str, mode: str | None = None) -> str:
                response = client.chat(
                    model=OLLAMA_MODEL,
                    messages=[
                        {"role": "system", "content": self._build_system_prompt(mode)},
                        {"role": "user",   "content": text},
                    ],
                    keep_alive=OLLAMA_KEEP_ALIVE,
                )
                return response.message.content.strip()

            return call

        except Exception as e:
            log.warning(
                "Ollama unavailable (%s) — is Ollama running? Start: ollama serve. Falling back to raw.", e
            )
            self._enabled = False
            return None

    def _setup_anthropic(self):
        try:
            import anthropic
            # Windows Credential Manager takes precedence; env var is the fallback
            api_key = None
            try:
                import keyring
                api_key = keyring.get_password("Clembot-dictate", "anthropic_api_key")
            except Exception:
                pass
            if not api_key:
                api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                log.warning(
                    "REFINE_BACKEND=anthropic but no API key found. "
                    "Add it in Settings → AI Key, or set ANTHROPIC_API_KEY env var. "
                    "Falling back to raw."
                )
                self._enabled = False
                return None

            client = anthropic.Anthropic(api_key=api_key)
            log.info("Anthropic ready — model: %s", ANTHROPIC_MODEL)

            def call(text: str, mode: str | None = None) -> str:
                response = client.messages.create(
                    model=ANTHROPIC_MODEL,
                    max_tokens=1024,
                    system=self._build_system_prompt(mode),
                    messages=[{"role": "user", "content": text}],
                )
                return response.content[0].text.strip()

            return call

        except ImportError:
            log.error("anthropic package not installed. Run: pip install anthropic")
            self._enabled = False
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def refine(self, raw: str, mode: str | None = None) -> str:
        """Return cleaned transcript. Falls back to raw on any error."""
        if not self._enabled or not self._call or not raw.strip():
            return raw

        try:
            t0 = time.perf_counter()
            refined = self._call(raw, mode)
            elapsed = time.perf_counter() - t0
            log.debug("%.2fs  mode=%r  raw=%r  →  refined=%r", elapsed, mode, raw, refined)
            return refined if refined else raw

        except Exception as e:
            log.error("Refinement error (%s) — using raw transcript.", e)
            return raw
