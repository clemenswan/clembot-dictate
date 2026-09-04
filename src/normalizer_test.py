"""
Manual test for the output normaliser. Run:  python src/normalizer_test.py

Matches the house style of hotkey_test.py / paste_test.py: a script you run and
read, not a pytest suite.

The point of these cases is the SECOND group. Stripping zero-width spaces is
easy; the way this feature would do real damage is by eating a character that
was load-bearing. Emoji ZWJ sequences, variation selectors, flag tag runs and
script joiners must survive untouched.
"""

import sys

from normalizer import is_available, normalize, plan_clipboard_clean

# Carriers: should be removed or normalised.
STRIP = [
    ("zero-width space", "Shipping​ beats planning.", "Shipping beats planning."),
    ("non-breaking space", "30 things", "30 things"),
    ("narrow no-break space", "30 things", "30 things"),
    ("word joiner", "no⁠thing", "nothing"),
    ("combining grapheme joiner", "a͏b", "ab"),
]

# Load-bearing: must survive byte-for-byte.
PRESERVE = [
    ("emoji ZWJ family", "family \U0001F468‍\U0001F469‍\U0001F467 here"),
    ("emoji + VS16", "heart ❤️ here"),
    ("flag tag sequence",
     "flag \U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F here"),
    ("Persian ZWNJ", "می‌خواهم"),
    ("accents", "Café naïve São Paulo"),
    ("plain ascii", "Just a normal sentence."),
]


def main() -> int:
    if not is_available():
        print("FAIL: normaliser unavailable (vendor/text_unicode.py missing?)")
        return 1

    failures = 0

    print("-- carriers should be stripped --")
    for name, src, want in STRIP:
        got, stats = normalize(src)
        ok = got == want
        failures += not ok
        print("%-28s %s  removed=%d replaced=%d"
              % (name, "ok" if ok else "FAIL", stats["removed"], stats["replaced"]))
        if not ok:
            print("     want: %s" % want.encode("unicode_escape").decode("ascii"))
            print("     got : %s" % got.encode("unicode_escape").decode("ascii"))

    print("\n-- load-bearing characters must survive --")
    for name, src in PRESERVE:
        got, _ = normalize(src)
        ok = got == src
        failures += not ok
        print("%-28s %s" % (name, "ok" if ok else "FAIL"))
        if not ok:
            print("     in : %s" % src.encode("unicode_escape").decode("ascii"))
            print("     out: %s" % got.encode("unicode_escape").decode("ascii"))

    print()
    print("-- clipboard clean decisions --")
    # A None replacement means "write nothing back". Getting this wrong either
    # rewrites the clipboard with an identical copy or, worse, with "".
    dirty = "Shipping" + chr(0x200B) + " beats" + chr(0xA0) + "planning."
    cases = [
        ("empty -> no write",         plan_clipboard_clean("")[0] is None),
        ("whitespace -> no write",    plan_clipboard_clean("   " + chr(10))[0] is None),
        ("already clean -> no write", plan_clipboard_clean("Plain text.")[0] is None),
        ("dirty -> writes cleaned",   plan_clipboard_clean(dirty)[0] == "Shipping beats planning."),
        ("dirty -> counts in message", "1 removed, 1 replaced" in plan_clipboard_clean(dirty)[1]),
        # The house-style half is NOT this function's job. If either of these
        # fails, something has started silently rewriting visible characters.
        ("em dash survives",          plan_clipboard_clean("a" + chr(0x2014) + "b")[0] is None),
        ("curly quotes survive",      plan_clipboard_clean(chr(0x201C) + "x" + chr(0x201D))[0] is None),
        ("every message is non-empty",
         all(plan_clipboard_clean(t)[1] for t in ("", "clean", dirty))),
    ]
    for name, ok in cases:
        failures += not ok
        print("%-28s %s" % (name, "ok" if ok else "FAIL"))

    print("\n-- must never raise, must never return None --")
    checks = [
        ("empty string", normalize("") == ("", {"removed": 0, "replaced": 0})),
        ("plain passthrough", normalize("hello")[0] == "hello"),
    ]
    for name, ok in checks:
        failures += not ok
        print("%-28s %s" % (name, "ok" if ok else "FAIL"))

    print("\n%s" % ("ALL PASS" if failures == 0 else "%d FAILURE(S)" % failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
