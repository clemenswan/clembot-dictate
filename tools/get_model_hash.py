"""
Prints the SHA256 of model.bin for the faster-whisper model currently in cache.

Run once after the first successful launch (which downloads the model):
    python tools\get_model_hash.py

Then paste the printed value into config.py as MODEL_SHA256.
"""

import hashlib
import sys
from pathlib import Path

MODEL_SIZE = "tiny"

snapshots = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / f"models--Systran--faster-whisper-{MODEL_SIZE}"
    / "snapshots"
)

if not snapshots.exists():
    print(f"No model cache found at: {snapshots}")
    print("Launch Clembot-dictate once to trigger the download, then re-run this script.")
    sys.exit(1)

snap_dirs = sorted(d for d in snapshots.iterdir() if d.is_dir())
if not snap_dirs:
    print("Snapshot directory is empty — model may not have finished downloading.")
    sys.exit(1)

model_bin = snap_dirs[-1] / "model.bin"
if not model_bin.exists():
    print(f"model.bin not found in: {snap_dirs[-1]}")
    sys.exit(1)

print(f"Hashing: {model_bin}")
sha256 = hashlib.sha256()
with open(model_bin, "rb") as f:
    for chunk in iter(lambda: f.read(65536), b""):
        sha256.update(chunk)

digest = sha256.hexdigest()
print(f"\nSHA256: {digest}")
print(f'\nAdd to src/config.py:\n    MODEL_SHA256 = "{digest}"')
