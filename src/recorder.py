"""
Mic capture using sounddevice.
Records while the hotkey is held, accumulates chunks into a buffer.
Returns a raw numpy float32 array — no temp file, no disk I/O.
"""

import threading
import numpy as np
import sounddevice as sd

from logger import get_logger
from config import SAMPLE_RATE, CHANNELS, AUDIO_DEVICE

log = get_logger("recorder")


class Recorder:
    @staticmethod
    def check_mic_access() -> bool:
        """Open the default mic briefly to verify access. Returns False if denied or unavailable."""
        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", blocksize=512
            ):
                pass
            return True
        except Exception as e:
            log.warning("Mic access check failed: %s", e)
            return False

    def __init__(self):
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None

    def start(self) -> bool:
        """Open the mic and begin recording. Returns False if the device is unavailable."""
        with self._lock:
            self._chunks = []

        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                device=AUDIO_DEVICE,
                callback=self._callback,
            )
            self._stream.start()
            return True
        except Exception as e:
            log.error("Failed to open mic: %s", e)
            self._stream = None
            return False

    def _callback(self, indata: np.ndarray, frames: int, time, status):
        if status:
            log.warning("sounddevice status: %s", status)
        with self._lock:
            self._chunks.append(indata.copy())

    def stop(self) -> np.ndarray | None:
        """Stop recording. Returns float32 mono array at SAMPLE_RATE, or None if empty."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            chunks = list(self._chunks)
            self._chunks = []

        if not chunks:
            return None

        return np.concatenate(chunks, axis=0).flatten()
