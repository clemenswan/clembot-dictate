"""
Output normalisation — strips invisible characters from text before it is pasted.

WHY THIS EXISTS
  Dictation output does not go straight from Whisper to your cursor. It passes
  through `refiner.py`, which is an LLM (local Ollama by default, the Anthropic
  API optionally). LLMs emit non-breaking spaces, narrow no-break spaces, zero
  width spaces and word joiners. Those land invisibly in whatever you were
  typing into, and they break search, diff and word counts wherever that text
  ends up.

  This is output hygiene, not watermark removal. It strips characters you cannot
  see. It does NOT touch statistical token-sampling watermarks, which live in
  word choice, and it proves nothing about authorship.

DESIGN RULE
  This must never be the reason a dictation fails. Every failure path returns
  the input unchanged. A normalisation bug costs you an invisible character;
  a raised exception costs you the sentence you just spoke.
"""

from logger import get_logger

log = get_logger(__name__)

try:
    from vendor.text_unicode import clean_text as _clean_text
    _AVAILABLE = True
except Exception as exc:  # pragma: no cover - import guard
    log.warning("Output normaliser unavailable (%s); text will pass through raw.", exc)
    _clean_text = None
    _AVAILABLE = False


def is_available() -> bool:
    return _AVAILABLE


def normalize(text: str) -> tuple[str, dict]:
    """Return (cleaned_text, stats). Never raises, never returns None.

    stats is {"removed": int, "replaced": int} and is zeroed whenever the pass
    could not run, so callers can log it unconditionally.
    """
    empty = {"removed": 0, "replaced": 0}
    if not text or not _AVAILABLE:
        return text, empty

    try:
        # Stock defaults on purpose. strip_emoji_glue stays False: it is upstream's
        # paranoid mode and it would break emoji sequences, Arabic and Persian
        # joiners, Devanagari and Hangul jamo. See vendor/ATTRIBUTION.md.
        cleaned, stats = _clean_text(text)
    except Exception as exc:
        log.warning("Output normalisation failed (%s); pasting raw text.", exc)
        return text, empty

    if not isinstance(cleaned, str):
        log.warning("Output normaliser returned %s; pasting raw text.", type(cleaned))
        return text, empty

    stats = stats or {}
    return cleaned, {
        "removed": stats.get("removed_count", 0),
        "replaced": stats.get("replaced_count", 0),
    }


def plan_clipboard_clean(text: str) -> tuple[str | None, str]:
    """Decide what a clipboard clean should do, without doing any of it.

    Pure by design: no clipboard, no tray, no logging. The I/O wrapper in
    main.py is three lines because everything worth getting wrong lives here,
    where normalizer_test.py can reach it.

    Returns (replacement, message). A None replacement means write nothing back,
    which covers all three no-op cases: nothing on the clipboard, nothing to
    change, and no engine to change it with.
    """
    if not _AVAILABLE:
        return None, "Cleaner unavailable. The text engine did not load."
    if not text or not text.strip():
        return None, "Clipboard is empty. Nothing to clean."

    cleaned, stats = normalize(text)
    if cleaned == text:
        return None, "Already clean. No invisible characters found."

    return cleaned, "Cleaned: %d removed, %d replaced." % (
        stats["removed"], stats["replaced"])


def describe_changes(original: str) -> list[str]:
    """Human lines for what a clean did to `original`. Never raises.

    Derived on demand rather than stored on the history entry. The engine is the
    authority on what it changed, and a description saved next to the text would
    go stale the moment the engine is updated while the text stayed the same.

    Returns [] when nothing changed or the engine is unavailable, so a caller can
    treat "no lines" as "nothing to say".
    """
    if not original or not _AVAILABLE:
        return []
    try:
        _, stats = _clean_text(original)
    except Exception as exc:
        log.warning("Change description failed (%s).", exc)
        return []

    lines = []
    for bucket, verb in (("removed", "removed"), ("replaced", "replaced")):
        for name, count in sorted((stats or {}).get(bucket, {}).items()):
            lines.append("%d %s %s" % (count, _friendly(name), verb))
    return lines


def _friendly(name: str) -> str:
    """'U+200B ZERO WIDTH SPACE (Cf)' -> 'zero width space'.

    The codepoint and the Unicode general category are correct, and are noise to
    anyone who is not debugging this. The name is the part that says what it was.
    """
    parts = name.split()
    if parts and parts[0].startswith("U+"):
        parts = parts[1:]
    if parts and parts[-1].startswith("("):
        parts = parts[:-1]
    return " ".join(parts).lower() or name
