"""Design tokens. The only place a colour, size or radius is written down.

Derived from the Wanessa Labs system (`wanessalabs-astro/design/brand.md`), which is
a warm-sand light palette for the web front door. This app is a dark utility that sits
above whatever you are working in, so the palette is that system inverted rather than a
different one: neutrals keep the warm hue 82, and the accent keeps the one forest green
at hue 152, lightened so it carries on a dark ground.

What it replaces: Catppuccin Mocha, a third-party dev theme in cool indigo and cyan.
It is a fine theme and it is not this product's.

Every contrast number below is measured, not asserted, per the brand file's own rule.
Measured 2026-08-20 against WCAG 2.1 relative luminance:

    text_primary    16.87 : 1 on bg      AAA
    text_secondary  10.44 : 1 on bg      AAA
    text_muted       6.30 : 1 on bg      AA  (5.10 on surface_raised, still AA)
    accent           7.17 : 1 on bg      AAA
    recording        5.83 : 1 on bg      AA
    on_accent        7.17 : 1 on accent  AAA

The OKLCH source is kept beside each hex so the next person can re-derive rather than
guess. Nothing here is eyeballed.
"""

from __future__ import annotations

import tkinter.font as tkfont

# ---------------------------------------------------------------------------
# Colour
# ---------------------------------------------------------------------------

# Neutrals: hue 82, the warm sand axis, inverted for a dark surface.
BG             = "#0e0c08"   # oklch(15.5% 0.008 82)  window ground
SURFACE        = "#191712"   # oklch(20.5% 0.010 82)  cards, rows
SURFACE_RAISED = "#26221c"   # oklch(25.5% 0.012 82)  controls, chips, inputs
BORDER         = "#34312c"   # oklch(31.5% 0.010 82)  hairline
BORDER_ACTIVE  = "#59554d"   # oklch(45.0% 0.014 82)  hover, focus

TEXT_PRIMARY   = "#f0eeeb"   # oklch(95.0% 0.005 82)
TEXT_SECONDARY = "#c0bdb9"   # oklch(80.0% 0.007 82)
TEXT_MUTED     = "#95928d"   # oklch(66.0% 0.008 82)  labels only, never body

# The one forest green. Do not introduce a second green.
ACCENT         = "#51af6f"   # oklch(68.0% 0.130 152)
ACCENT_HOVER   = "#72c78b"   # oklch(76.0% 0.120 152)
ACCENT_DIM     = "#1b3422"   # oklch(30.0% 0.045 152) fill only, never text
ACCENT_DIM_HOVER = "#25452f" # oklch(36.0% 0.055 152) hover for the above
HOVER          = "#34312c"   # oklch(31.5% 0.010 82)  neutral control hover
ON_ACCENT      = "#0e0c08"   # oklch(15.5% 0.010 82)

# Status ramp. Functional only: these never decorate.
RECORDING      = "#e76250"   # oklch(66.0% 0.170  30)
RECORDING_DIM  = "#76382e"   # oklch(42.0% 0.090  30) the off half of the pulse
STATUS_OK      = "#4fb772"   # oklch(70.0% 0.140 152)
STATUS_WARN    = "#e0af3b"   # oklch(78.0% 0.140  85)
STATUS_INFO    = "#58a7dc"   # oklch(70.0% 0.110 240)

# ---------------------------------------------------------------------------
# Spacing and shape
# ---------------------------------------------------------------------------

# 4pt scale, same as the brand. Named so a stray 7px cannot happen by accident.
SP_1, SP_2, SP_3, SP_4, SP_5, SP_6 = 4, 8, 12, 16, 24, 32

RADIUS_SM, RADIUS_MD, RADIUS_LG = 3, 6, 8
RADIUS_FULL = 999

# Control heights. Two, not five: one for real controls, one for chips.
CONTROL_H = 28
CHIP_H = 20

# Elevation is borders only. The brand file bans shadows on this brand outright,
# and the games hub's shadow ramp is hub-scoped and must not leak here.

# ---------------------------------------------------------------------------
# Type
# ---------------------------------------------------------------------------

# The brand families (Bricolage Grotesque, Archivo, Barlow Condensed) are web fonts
# and are not installed here, so the app uses what Windows ships and keeps the part
# of the brand that is actually load-bearing: one scale, and the uppercase tracked
# micro-label. `_pick` degrades rather than guessing, because a missing family in Tk
# silently falls back to something that looks nothing like the intent.
_DISPLAY_STACK = ("Segoe UI Variable Display", "Segoe UI Semibold", "Segoe UI", "Arial")
_BODY_STACK    = ("Segoe UI Variable Text", "Segoe UI", "Arial")
_MONO_STACK    = ("Cascadia Mono", "Consolas", "Courier New")

# One scale. Anything not in this list is a mistake, including the 9px that used to
# be scattered through the header.
SIZE_TITLE, SIZE_BODY, SIZE_SMALL, SIZE_LABEL = 15, 12, 11, 10

# Tk has no letter-spacing, so the tracked micro-label is spelled out per character.
LABEL_TRACKING = " "


def _pick(stack: tuple[str, ...]) -> str:
    """First installed family in the stack, else Tk's default."""
    try:
        available = set(tkfont.families())
    except Exception:                       # no Tk root yet, or headless
        return stack[-1]
    return next((name for name in stack if name in available), stack[-1])


def display() -> str:
    return _pick(_DISPLAY_STACK)


def body() -> str:
    return _pick(_BODY_STACK)


def mono() -> str:
    return _pick(_MONO_STACK)


def track(text: str) -> str:
    """Wide-tracked uppercase, the brand's one unmistakable signature.

    `HISTORY` becomes `H I S T O R Y`. Only for labels under 12px, never for
    running text, and never long enough to wrap.
    """
    return LABEL_TRACKING.join(text.upper())
