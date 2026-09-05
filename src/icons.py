"""Small icons drawn with lines and arcs, not typed as emoji.

The header used to be built from `●`, `▼`, `⚙`, `⟳`, `📋` and `✕`. Emoji as an icon
system is a vault slop tell (`emoji-as-ui`, vault scope): emoji inside authored content
is fine, emoji as UI furniture is not. It also renders differently on every machine,
picks up the system emoji font's colour rather than ours, and cannot be sized to a
grid, which is most of why the old bar looked assembled rather than designed.

These are drawn on a plain `tkinter.Canvas`. Tk has no alpha, so each icon takes the
colour of the surface it sits on and repaints on state change. Every icon is defined
on a square box and centred, so they line up on one optical baseline.
"""

from __future__ import annotations

import tkinter as tk


class Icon(tk.Canvas):
    """A square canvas that redraws itself when its colour changes."""

    def __init__(self, master, size: int, bg: str, color: str, **kwargs):
        super().__init__(master, width=size, height=size, bg=bg,
                         highlightthickness=0, bd=0, **kwargs)
        self._size = size
        self._color = color
        self._bg = bg
        self.draw()

    def set_color(self, color: str):
        if color != self._color:
            self._color = color
            self.draw()

    def set_bg(self, bg: str):
        if bg != self._bg:
            self._bg = bg
            self.configure(bg=bg)
            self.draw()

    def draw(self):
        self.delete("all")


class Dot(Icon):
    """Status dot. Reads as a light, not as a bullet character."""

    def __init__(self, master, bg: str, color: str, size: int = 10, radius: int = 4):
        self._radius = radius
        super().__init__(master, size, bg, color)

    def draw(self):
        self.delete("all")
        c = self._size / 2
        r = self._radius
        self.create_oval(c - r, c - r, c + r, c + r, fill=self._color, outline="")


class Chevron(Icon):
    """Two strokes. Points down when closed, up when open."""

    def __init__(self, master, bg: str, color: str, size: int = 12, up: bool = False):
        self._up = up
        super().__init__(master, size, bg, color)

    def set_up(self, up: bool):
        if up != self._up:
            self._up = up
            self.draw()

    def draw(self):
        self.delete("all")
        s = self._size
        pad = s * 0.28
        mid = s / 2
        if self._up:
            pts = [(pad, mid + pad / 2), (mid, mid - pad / 2), (s - pad, mid + pad / 2)]
        else:
            pts = [(pad, mid - pad / 2), (mid, mid + pad / 2), (s - pad, mid - pad / 2)]
        self.create_line(*[c for p in pts for c in p],
                         fill=self._color, width=1.6, capstyle="round", joinstyle="round")


class Menu(Icon):
    """Three rules. Opens settings; deliberately not a gear, which needs detail
    this size cannot carry without turning to mush."""

    def __init__(self, master, bg: str, color: str, size: int = 14):
        super().__init__(master, size, bg, color)

    def draw(self):
        self.delete("all")
        s = self._size
        pad = s * 0.2
        for i in range(3):
            y = s * 0.3 + i * (s * 0.2)
            self.create_line(pad, y, s - pad, y, fill=self._color, width=1.4,
                             capstyle="round")


class Close(Icon):
    """A cross of two strokes, at the same weight as everything else."""

    def __init__(self, master, bg: str, color: str, size: int = 12):
        super().__init__(master, size, bg, color)

    def draw(self):
        self.delete("all")
        s = self._size
        pad = s * 0.3
        self.create_line(pad, pad, s - pad, s - pad, fill=self._color, width=1.4,
                         capstyle="round")
        self.create_line(s - pad, pad, pad, s - pad, fill=self._color, width=1.4,
                         capstyle="round")


class Grip(Icon):
    """Two short rules marking the draggable area of a frameless window.

    Without a title bar there is nothing that says "you can move this", so the
    affordance has to be drawn. It is the quietest thing in the bar on purpose.
    """

    def __init__(self, master, bg: str, color: str, size: int = 12):
        super().__init__(master, size, bg, color)

    def draw(self):
        self.delete("all")
        s = self._size
        for y in (s * 0.38, s * 0.62):
            self.create_line(s * 0.25, y, s * 0.75, y, fill=self._color, width=1.2,
                             capstyle="round")


class Mic(Icon):
    """A microphone, for the empty state.

    The empty state used a 34px emoji, which broke two rules at once: emoji as
    UI furniture is a vault tell, and 34 is not on the type scale. Drawn here it
    takes the surface colour like every other icon.

    The capsule is an ellipse rather than two lines closed by two arcs. The
    first attempt did it the hard way and put the straight sides at
    top + bw = 10.1 down to bot - bw = 8.4: a negative length, so the body
    vanished and it rendered as a ring above a smile. An ellipse cannot be
    inside out.
    """

    def __init__(self, master, bg: str, color: str, size: int = 28):
        super().__init__(master, size, bg, color)

    def draw(self):
        self.delete("all")
        s = self._size
        w = max(1.4, s * 0.055)
        cx = s / 2

        # Capsule.
        half_w, top, bot = s * 0.17, s * 0.08, s * 0.55
        self.create_oval(cx - half_w, top, cx + half_w, bot,
                         outline=self._color, width=w)

        # Cradle, then the stem down to the base.
        cw = s * 0.30
        self.create_arc(cx - cw, bot - cw * 1.15, cx + cw, bot + cw * 0.85,
                        start=200, extent=140, style="arc",
                        outline=self._color, width=w)
        self.create_line(cx, bot + cw * 0.55, cx, s * 0.92,
                         fill=self._color, width=w, capstyle="round")
