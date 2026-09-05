# Changelog

## 1.3.0

Cleaning the clipboard now leaves something behind.

**A clean can be undone.** The clipboard has no undo of its own, so until now
cleaning was a one-way door: a tray balloon told you what changed and then it was
gone, along with the original. Every clean is recorded in the history panel now,
and **Restore** puts the original text back on your clipboard.

**A cleaned entry shows what changed, not before and after.** Cleaning only ever
touches characters you cannot see, so two blocks of text would render the same
sentence twice and teach you nothing. The card lists the actual tally instead:
`1 zero width space removed`, `1 no-break space replaced`. Underneath is what is
sitting on your clipboard now.

**Questions you asked appear too.** A voice command used to be filed as a
dictation whose transcript had gone missing. It is its own kind now, with what
the sidecar heard and the answer it spoke.

**Clean is a control on the bar**, next to History. Asking a question is not, on
purpose: cleaning is one-shot and a click maps to it exactly, while asking is
hold-to-talk, and a click could only mean start-then-click-again-to-stop. That is
a mode, and a mode you forget you are in pastes an answer into a document.

**One thing worth knowing.** Recording a clean writes that clipboard text to
`history.json`, which before this release held only your own dictations. If you
clean something you would rather not keep on disk, set
`CLIPBOARD_CLEAN_HISTORY = False`. Cleaning still works; it just cannot be undone.

The bar is 580px wide rather than 520. At the old width the new control pushed
the `AI` label into the status text.

## 1.2.1

The interface now says what the app can do.

**Two shipped features were invisible.** Voice commands landed in 1.1.0 and clipboard
cleaning in 1.2.0, and the interface mentioned neither. Searching the UI source for
`Ctrl` and `Shift` returned nothing at all. Both were in this README, which is not the
same as discoverable: nobody reads the README of a tool that is already installed and
working.

**Every shortcut is listed in two places now.** A **Shortcuts** section at the top of
Settings, which is permanent, and the history panel before your first dictation, which
previously spent its whole area on one chord and a microphone glyph. Both are built
from one list that reads your config, so a feature you switch off is not advertised at
you. The first-run notification reads the same list.

**The compact bar is deliberately unchanged.** It is 44 pixels tall and its restraint
is the point. A feature list does not go there.

**A Text section in Settings** explains the invisible-character cleaning, including the
part the docs are careful about: it is not watermark removal and it proves nothing
about authorship. A claim that only appears in the documentation is a claim the person
using the thing never sees.

Six smaller fixes came out of looking properly, all of them things that had been
shipping for a while:

- The empty state drew a 34px emoji. Emoji take the system font's colour rather than
  the app's and cannot sit on a grid, which is why the rest of the interface stopped
  using them a release ago. It is drawn now.
- The history panel heading was 9px and untracked while the bar's own label was
  letter-spaced, so the two never matched.
- Two colours were hardcoded leftovers from a third-party theme this app replaced.
- Status messages carried a bullet character that got letter-spaced and painted next
  to the real status dot, so a cold start read `* L O A D I N G . . .` beside a dot.
- The Settings dialog had a fixed height and quietly cut off its last paragraph as
  soon as it grew.
- Three labels sat at 8px and 9px on a four-size type scale.

`tools/check_brand.py` is new and fails the build on the mechanical version of those
rules: a colour written outside the palette file, a font size off the scale, an emoji
or an em dash in text a user reads. Every one of the six was mechanically detectable
and nothing was checking. It found the last three itself.

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
