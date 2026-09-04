# Vendored: text_unicode.py

| | |
|---|---|
| Source | `github.com/guillaumemeyer/watermarks-remover` |
| Path | `service/scripts/text_unicode.py` |
| Commit | `946e4fc57ebfc835b7d45f00beed1f1d90eb173f` |
| Blob | `e1b406bdc544407afdf27c3034d5fea44e88b194` |
| License | MIT (`LICENSE-watermarks-remover`, retained verbatim) |
| Vendored | 2026-09-03 |
| Modified | **No.** Byte-identical to the upstream blob. |

## Why vendored rather than called over HTTP

ClemVault runs this engine as a local HTTP service in a Docker container, and the
vault's own rule is that the service is the only cleaner. **That rule does not
apply here, deliberately.**

Clembot-dictate is a publicly released MIT product with an installer. Requiring
Docker Desktop so a dictation app can normalise its own output would be absurd for
every user who installs it. The engine is 730 lines of pure stdlib (`unicodedata`,
`collections`, `dataclasses`, `difflib`), so vendoring costs one file and no
dependencies.

The vault-side carve-out is recorded in `voice-transcriber/CLAUDE.md`.

## Why not hand-rolled

Some invisible characters are load-bearing: emoji ZWJ sequences, variation
selectors, Arabic and Persian joiners, Devanagari, Hangul jamo fillers, flag tag
runs. This engine preserves those and strips only the carriers. A regex would
corrupt real text invisibly, which is exactly the failure this is meant to prevent.

## What we call

`clean_text(text)` with stock defaults: `normalize_spaces=True`,
`strip_emoji_glue=False`, `nfkc=False`, `aggressive_homoglyphs=False`,
`strip_bidi=False`.

**`strip_emoji_glue` must stay False.** It is the upstream "paranoid mode" and it
strips ZWJ and variation selectors unconditionally, which breaks emoji and several
writing systems.

## Updating

Re-copy from the same upstream path at a newer commit, verify the blob hash, and
update this file. Do not edit the vendored file in place.
