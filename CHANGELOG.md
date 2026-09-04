# Changelog

## 1.2.0

Text hygiene, in two places.

**Every dictation is now stripped of invisible characters before it reaches your cursor.**
The AI cleanup pass runs your words through a language model, and language models emit
zero-width spaces, word joiners, non-breaking spaces and narrow no-break spaces. You never
see them. The next tool to read that text does: search misses, diffs light up, word counts
drift. Every dictation is cleaned now, refined or raw, and `NORMALIZE_OUTPUT = False`
turns it off.

**Tap Shift and the hotkey to clean your clipboard the same way.** Copy from anywhere,
a chat window with an assistant in it being the obvious case, tap the chord, and the
clipboard is replaced in place. A tray balloon says what changed, or says there was
nothing to change. It is on the tray menu too, as **Clean clipboard**. It needs no model
and no network, so it works while the speech model is still downloading on a fresh
install.

**Visible punctuation is left alone**, deliberately. Em dashes, curly quotes and ellipses
are ordinary characters that ordinary writing uses, and editing your prose is not this
tool's job. Lookalike letters are left alone too: a Cyrillic "a" in a Latin word is not
converted, because the safe cases and the destructive ones are hard to tell apart without
knowing what language you meant.

**It is not watermark removal and it proves nothing about authorship.** Text can be marked
statistically, in word choice rather than in the bytes, and nothing here touches that. The
claim this project will not make is that cleaned text is undetectable or human-written.
The one it will make is narrower: what you paste stops carrying invisible characters that
confuse the next tool to read it.

**Invisible does not mean disposable.** Emoji combine with zero-width joiners, flags are
built from tag sequences, and Arabic, Persian, Devanagari, Hangul and Mongolian use
joiners that carry meaning. Stripping those would corrupt real text silently, which is a
worse failure than the one this fixes. The engine keeps them and takes only free-floating
carriers, and `src/normalizer_test.py` asserts it: an emoji family, a heart with a
variation selector, a flag tag sequence, and a Persian word whose meaning depends on its
joiner.

The engine is vendored rather than reimplemented: about 730 lines of pure standard
library, MIT, from [watermarks-remover](https://github.com/guillaumemeyer/watermarks-remover).
Nothing is sent anywhere. `src/vendor/ATTRIBUTION.md` records the exact commit.

## 1.1.1

An interface pass.

**The window lost its title bar.** A 44px strip was carrying 32px of chrome whose
minimise and maximise buttons meant nothing for a tray tool. It is frameless now, drag
it by the bar, and it stays on top since it no longer has a taskbar entry.

**A palette of its own.** The interface was painted in Catppuccin Mocha, a third-party
developer theme, in sixteen hardcoded colours. It now derives a warm dark palette with a
forest green accent from the Wanessa Labs system, in one file. Every text colour was
measured against its background; the lowest ratio in the app is 5.1:1.

**Icons instead of emoji.** The header was built from `●`, `▼`, `⚙`, `⟳`, `📋` and `✕`,
which take the system emoji font's colour rather than the app's and cannot be sized to a
grid. They are drawn now, at one stroke weight.

**History cards fit their contents.** Every entry was padded to three lines regardless of
length, so a full panel showed one and a half of them. A card built before the panel was
open had no width yet, so a one-line transcript measured as three and stayed that way.
Fixed, and two entries now fit where one and a half did.

**Type has a scale**: four sizes, one family, state words set as spaced uppercase labels.
Previously four sizes at three weights with nothing behind the choice.

The tray icon is on the palette too, green when idle rather than slate.

## 1.1.0

**Voice commands (optional).** Hold Ctrl with the hotkey and the utterance becomes a
spoken question instead of pasted text, answered by a local sidecar process. Ctrl is
sampled at key-down, so it is per utterance rather than a mode. With no sidecar running
the utterance falls back to ordinary dictation and the tray says why, so the feature is
dormant rather than broken. The sidecar itself is not published yet.

**Fixed: the update check could never have worked.** It sent Python's default
`urllib` user agent, which Cloudflare's managed rules reject on every path of the host
serving the version manifest, and the check swallows exceptions by design. It had failed
silently since it was written. It now sends a named agent.

**Added `tools/check_release.py`.** Compares every file that names a version, checks the
installer exists, and probes the update endpoint using the agent read out of `updater.py`,
because checking with a different client than the app uses proves nothing about the app.
Written after three files shipped a release still naming the previous version.

## 1.0.0

First public build.

- Hold-to-speak, release-to-paste, in any Windows app
- Local transcription with faster-whisper, in memory, no temporary files
- Optional text cleanup with Ollama (local) or Claude (cloud)
- Context modes selected automatically from the foreground window
- History with the raw transcript and the cleaned version side by side
- System tray, live hotkey rebinding, clipboard-only mode
- Single-instance guard, crash handlers, rotating log, microphone permission check
- Inno Setup installer, no admin rights, upgrades in place
