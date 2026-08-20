"""
faster-whisper transcription wrapper.
Model is loaded once at startup and reused for all subsequent dictations.
Accepts a numpy float32 array directly — no temp file required.
"""

import hashlib
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

from logger import get_logger
from config import MODEL_SIZE, MODEL_SHA256

log = get_logger("transcriber")


class Transcriber:
    @staticmethod
    def is_cached() -> bool:
        """Return True if the model weights are already in the local HuggingFace cache."""
        snapshots = (
            Path.home()
            / ".cache"
            / "huggingface"
            / "hub"
            / f"models--Systran--faster-whisper-{MODEL_SIZE}"
            / "snapshots"
        )
        try:
            return snapshots.exists() and any(snapshots.iterdir())
        except Exception:
            return False

    def __init__(self):
        cache_dir = (
            Path.home() / ".cache" / "huggingface" / "hub"
            / f"models--Systran--faster-whisper-{MODEL_SIZE}"
        )
        if self.is_cached():
            log.info("Loading %s model from cache: %s", MODEL_SIZE, cache_dir)
        else:
            log.info("Downloading %s model — first run (~75 MB). Cache: %s", MODEL_SIZE, cache_dir)
        self._model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
        self._verify_model_integrity()
        log.info("Model ready.")

    def _verify_model_integrity(self):
        """SHA256-check model.bin against MODEL_SHA256 in config. Skipped when None."""
        if MODEL_SHA256 is None:
            return
        snapshots = (
            Path.home() / ".cache" / "huggingface" / "hub"
            / f"models--Systran--faster-whisper-{MODEL_SIZE}"
            / "snapshots"
        )
        try:
            snap_dirs = sorted(d for d in snapshots.iterdir() if d.is_dir())
            if not snap_dirs:
                log.warning("Integrity check skipped — no snapshot directory found.")
                return
            model_bin = snap_dirs[-1] / "model.bin"
            if not model_bin.exists():
                log.warning("Integrity check skipped — model.bin not found.")
                return
            sha256 = hashlib.sha256()
            with open(model_bin, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            actual = sha256.hexdigest()
            if actual != MODEL_SHA256:
                raise ValueError(
                    f"Model integrity check FAILED.\n"
                    f"Expected: {MODEL_SHA256}\n"
                    f"Got:      {actual}\n"
                    f"Delete {snapshots} and restart to re-download a clean copy."
                )
            log.info("Model integrity verified.")
        except ValueError:
            raise
        except Exception as e:
            log.warning("Integrity check error (non-fatal): %s", e)

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe a float32 mono audio array. Returns stripped transcript (may be empty)."""
        segments, _ = self._model.transcribe(audio, beam_size=1, vad_filter=True)
        return " ".join(s.text for s in segments).strip()
