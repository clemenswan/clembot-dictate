"""
Transcription history — persisted to JSON.
Thread-safe via a lock; all mutations go through add().

Each Entry stores both the raw Whisper transcript and the AI-refined version.
Backward-compatible: entries without 'raw' in history.json load with raw="".
"""

import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List


def _data_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    d = base / "Clembot-dictate"
    d.mkdir(parents=True, exist_ok=True)
    return d


HISTORY_FILE = str(_data_dir() / "history.json")
HISTORY_MAX = 50


@dataclass
class Entry:
    timestamp: str        # ISO 8601
    text: str             # AI-refined (what was pasted)
    raw: str = field(default="")   # Raw Whisper transcript — "" if same as text or AI off

    @property
    def display_time(self) -> str:
        try:
            return datetime.fromisoformat(self.timestamp).strftime("%H:%M")
        except ValueError:
            return self.timestamp

    @property
    def has_refinement(self) -> bool:
        """True if raw and refined text are meaningfully different."""
        return bool(self.raw) and self.raw.strip() != self.text.strip()


class History:
    def __init__(self):
        self._lock = threading.Lock()
        self._entries: List[Entry] = self._load()

    def add(self, text: str, raw: str = "") -> Entry:
        entry = Entry(timestamp=datetime.now().isoformat(), text=text, raw=raw)
        with self._lock:
            self._entries.insert(0, entry)
            if len(self._entries) > HISTORY_MAX:
                self._entries = self._entries[:HISTORY_MAX]
            self._save(self._entries)
        return entry

    def update_text(self, entry: Entry, new_text: str):
        """Update the refined text of an existing entry in place and re-save."""
        with self._lock:
            entry.text = new_text
            self._save(self._entries)

    def get_all(self) -> List[Entry]:
        with self._lock:
            return list(self._entries)

    def _load(self) -> List[Entry]:
        path = os.path.abspath(HISTORY_FILE)
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Backward-compat: old entries won't have 'raw'
            return [Entry(
                timestamp=r["timestamp"],
                text=r["text"],
                raw=r.get("raw", ""),
            ) for r in data]
        except Exception:
            return []

    def _save(self, entries: List[Entry]):
        path = os.path.abspath(HISTORY_FILE)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in entries], f, indent=2)
