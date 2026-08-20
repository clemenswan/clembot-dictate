"""
Audio cues — short tones played on record start and stop.

Uses sounddevice (already a dependency) to play synthesized sine waves
asynchronously. No extra packages required.

Controlled by AUDIO_CUES in config.py. Set to True to enable.
"""

from __future__ import annotations
import numpy as np
import sounddevice as sd

from logger import get_logger
from config import AUDIO_CUES, SAMPLE_RATE

log = get_logger("cues")

# Tone definitions: (frequency_hz, duration_ms, amplitude)
_START_TONE = (880, 80, 0.25)   # high ping  — recording begins
_STOP_TONE  = (440, 120, 0.20)  # low thud   — recording ends


def _play(freq: float, duration_ms: int, amplitude: float) -> None:
    """Generate and play a sine wave. Non-blocking (sounddevice streams async)."""
    frames  = int(SAMPLE_RATE * duration_ms / 1000)
    t       = np.linspace(0, duration_ms / 1000, frames, endpoint=False)
    # Sine with a short linear fade-out to avoid clicks
    wave    = amplitude * np.sin(2 * np.pi * freq * t).astype(np.float32)
    fade    = np.linspace(1.0, 0.0, min(int(SAMPLE_RATE * 0.02), frames))
    wave[-len(fade):] *= fade
    sd.play(wave, samplerate=SAMPLE_RATE)


def play_start() -> None:
    """Play the record-start cue (if AUDIO_CUES is enabled)."""
    if AUDIO_CUES:
        try:
            _play(*_START_TONE)
        except Exception as e:
            log.warning("start tone failed: %s", e)


def play_stop() -> None:
    """Play the record-stop cue (if AUDIO_CUES is enabled)."""
    if AUDIO_CUES:
        try:
            _play(*_STOP_TONE)
        except Exception as e:
            log.warning("stop tone failed: %s", e)
