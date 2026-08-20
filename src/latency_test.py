"""
Phase 0 — Transcription Latency Benchmark
Measures faster-whisper inference time on a short audio clip.

Generates a synthetic WAV (silence + a tone) if no real audio file is provided,
then transcribes it and reports elapsed time. For real accuracy numbers, record
a 5-10 second voice clip and pass it as an argument.

Usage:
    python latency_test.py                  # uses synthetic test WAV
    python latency_test.py path/to/clip.wav # uses your own recording
"""

import sys
import time
import tempfile
import os
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

MODEL_SIZES = ["tiny", "small"]
SAMPLE_RATE = 16000
SYNTHETIC_DURATION = 5  # seconds of audio to generate


def make_synthetic_wav(path: str, duration: int = SYNTHETIC_DURATION):
    """Write a WAV of silence (faster-whisper handles it gracefully)."""
    samples = np.zeros(duration * SAMPLE_RATE, dtype=np.float32)
    sf.write(path, samples, SAMPLE_RATE)
    print(f"Generated synthetic {duration}s WAV at {path}")


def benchmark(model_size: str, wav_path: str) -> dict:
    print(f"\nLoading model: {model_size} (CPU, int8)...")
    load_start = time.perf_counter()
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    load_elapsed = time.perf_counter() - load_start
    print(f"  Model loaded in {load_elapsed:.2f}s")

    print(f"Transcribing {wav_path}...")
    infer_start = time.perf_counter()
    segments, info = model.transcribe(wav_path, beam_size=1)
    text = " ".join(s.text for s in segments).strip()
    infer_elapsed = time.perf_counter() - infer_start

    return {
        "model": model_size,
        "load_s": round(load_elapsed, 2),
        "infer_s": round(infer_elapsed, 2),
        "total_s": round(load_elapsed + infer_elapsed, 2),
        "transcript": text or "(no speech detected — expected for synthetic audio)",
        "language": info.language,
        "language_prob": round(info.language_probability, 2),
    }


def main():
    wav_path = sys.argv[1] if len(sys.argv) > 1 else None
    using_synthetic = wav_path is None

    tmp = None
    if using_synthetic:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        wav_path = tmp.name
        make_synthetic_wav(wav_path)
    else:
        print(f"Using provided audio: {wav_path}")

    print(f"\nBenchmarking models: {MODEL_SIZES}")
    print("Note: first run downloads model weights (~hundreds of MB). Subsequent runs are fast.\n")

    results = []
    for size in MODEL_SIZES:
        try:
            r = benchmark(size, wav_path)
            results.append(r)
        except Exception as e:
            print(f"  ERROR with {size}: {e}")

    if using_synthetic and tmp:
        os.remove(tmp.name)

    print("\n--- Latency Results ---")
    print(f"{'Model':<8} {'Load':>8} {'Infer':>8} {'Total':>8}  Verdict")
    print("-" * 50)
    for r in results:
        verdict = "PASS (<3s)" if r["infer_s"] < 3.0 else "SLOW (>3s) — consider tiny model"
        print(f"{r['model']:<8} {r['load_s']:>7}s {r['infer_s']:>7}s {r['total_s']:>7}s  {verdict}")

    print()
    print("Key metric: Infer time (load happens once at startup, not per dictation).")
    print("Target: infer_s < 3.0s for acceptable dictation UX.")
    if results:
        best = min(results, key=lambda r: r["infer_s"])
        print(f"Recommended model for your machine: {best['model']} ({best['infer_s']}s infer)")


if __name__ == "__main__":
    main()
