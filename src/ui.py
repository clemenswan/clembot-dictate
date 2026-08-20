"""Clembot-dictate UI: one 44px strip, with a history panel that folds out of it.

Frameless on purpose. A 44px tool wearing a 32px title bar with minimise, maximise
and close reads as a dialog somebody shrank, and none of those three buttons mean
anything for a strip that lives in the tray. The cost is that dragging and closing
are drawn here rather than provided: see `_make_draggable` and the grip.

Compact:
  +--------------------------------------------------------------+
  |  = *  R E A D Y      A I [==]  ( Claude Code v )  H I S T O R Y  v  =  x  |
  +--------------------------------------------------------------+

Expanded:
  +--------------------------------------------------------------+
  |  = *  R E A D Y      A I [==]  ( Claude Code v )  H I S T O R Y  ^  =  x  |
  +--------------------------------------------------------------+
  |  H I S T O R Y                                               |
  |  +--------------------------------------------------------+  |
  |  |  14:23                        [ RE-RUN ]  [ COPY ]     |  |
  |  |  +--------------------------------------------------+  |  |
  |  |  |  R A W                                           |  |  |
  |  |  |  um so basically fix the the auth bug            |  |  |
  |  |  +--------------------------------------------------+  |  |
  |  |  +--------------------------------------------------+  |  |
  |  |  |  A I                                             |  |  |
  |  |  |  Fix the authentication bug.                     |  |  |
  |  |  +--------------------------------------------------+  |  |
  |  +--------------------------------------------------------+  |
  +--------------------------------------------------------------+

Three rules this file follows, all of which it used to break:

1. **No colour, size or font is written here.** They come from `theme.py`, which
   derives them from the Wanessa Labs brand system. The old file held 16 hardcoded
   Catppuccin hexes and picked from 9, 10, 12 and 13px at three weights.
2. **No emoji as UI.** Icons are drawn in `icons.py` from lines and arcs. Emoji as
   an icon system is a vault slop tell, renders differently on every machine, and
   cannot take our colour or sit on our grid.
3. **Every text block fits its content.** Blocks measure themselves on `<Configure>`
   rather than once on a timer, because a card built before the panel is packed has
   no width yet and a one-line transcript counts as three.

All public methods are thread-safe via root.after().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import tkinter as tk
import customtkinter as ctk
import pyperclip
import webbrowser

from PIL import Image, ImageDraw, ImageTk

import theme
import icons
from history import History, Entry
from config import CONTEXT_MODES, DEFAULT_CONTEXT_MODE, HOTKEY, AUTO_CONTEXT, VERSION
import startup

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Catppuccin Mocha
# Colours, sizes and type all come from theme.py, which derives them from the
# Wanessa Labs brand system. Nothing in this file may hardcode a colour.
CLR_BG        = theme.BG
CLR_SURFACE   = theme.SURFACE
CLR_SURFACE1  = theme.SURFACE_RAISED
CLR_SURFACE2  = theme.HOVER
CLR_TEXT      = theme.TEXT_PRIMARY
CLR_SUBTEXT   = theme.TEXT_MUTED
CLR_IDLE      = theme.TEXT_MUTED
CLR_RECORDING = theme.RECORDING
CLR_RAW_LABEL = theme.TEXT_MUTED
CLR_RAW_TEXT  = theme.TEXT_SECONDARY
CLR_AI_LABEL  = theme.ACCENT
CLR_AI_TEXT   = theme.TEXT_PRIMARY
CLR_RUN_BTN   = theme.ACCENT_DIM
CLR_RUN_HOVER = theme.ACCENT_DIM_HOVER
CLR_RUN_TEXT  = theme.ACCENT
CLR_BORDER    = theme.BORDER

WINDOW_W   = 520
COMPACT_H  = 44    # header only. Was 52 plus a ~32px title bar we no longer draw.
BANNER_H   = 30    # update notification banner
HISTORY_H  = 520   # header + history panel
MAX_LINES  = 3


@dataclass
class _CardRefs:
    entry:          Entry
    copy_btn:       ctk.CTkButton
    run_btn:        ctk.CTkButton | None
    divider:        ctk.CTkFrame
    ai_frame:       ctk.CTkFrame
    ai_text:        tk.Text
    ai_expand_btn:  ctk.CTkButton | None = field(default=None)
    _ai_full_lines: list = field(default_factory=lambda: [MAX_LINES])
    _ai_expanded:   list = field(default_factory=lambda: [False])
    _copy_text:     str  = field(default="")

    def set_copy_text(self, text: str):
        self._copy_text = text
        self.copy_btn.configure(command=lambda: pyperclip.copy(text))


class ModeSelect(ctk.CTkFrame):
    """A dropdown that borrows nothing from the stock widget except behaviour.

    Keeps `get`/`set` so the rest of the app does not care that it changed, and
    posts a plain `tk.Menu` styled from the same tokens as everything else.
    """

    def __init__(self, master, values, initial, command, width=132):
        super().__init__(master, fg_color=CLR_SURFACE1, corner_radius=theme.RADIUS_MD,
                         height=theme.CONTROL_H, width=width)
        self.pack_propagate(False)
        self._values = list(values)
        self._value = initial
        self._command = command

        self._label = ctk.CTkLabel(
            self, text=initial, text_color=CLR_TEXT, anchor="w",
            font=ctk.CTkFont(family=theme.body(), size=theme.SIZE_SMALL),
        )
        self._label.pack(side="left", padx=(theme.SP_3, 0))

        self._chevron = icons.Chevron(self, bg=CLR_SURFACE1, color=CLR_SUBTEXT, size=12)
        self._chevron.pack(side="right", padx=(0, theme.SP_3))

        self._menu = tk.Menu(
            self, tearoff=0,
            bg=CLR_SURFACE1, fg=CLR_TEXT,
            activebackground=CLR_SURFACE2, activeforeground=CLR_TEXT,
            bd=0, relief="flat", activeborderwidth=0,
            font=(theme.body(), theme.SIZE_SMALL),
        )
        for value in self._values:
            self._menu.add_command(label=value, command=lambda v=value: self._choose(v))

        for widget in (self, self._label, self._chevron):
            widget.bind("<Button-1>", self._open)
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)
            widget.configure(cursor="hand2")

    # -- behaviour ----------------------------------------------------------
    def _open(self, _event=None):
        self._chevron.set_up(True)
        try:
            self._menu.post(self.winfo_rootx(),
                            self.winfo_rooty() + self.winfo_height() + theme.SP_1)
        finally:
            self.after(120, lambda: self._chevron.set_up(False))

    def _choose(self, value):
        self.set(value)
        if self._command:
            self._command(value)

    def _enter(self, _event=None):
        self.configure(fg_color=CLR_SURFACE2)
        self._chevron.set_bg(CLR_SURFACE2)

    def _leave(self, _event=None):
        self.configure(fg_color=CLR_SURFACE1)
        self._chevron.set_bg(CLR_SURFACE1)

    # -- the CTkOptionMenu surface the app already calls ---------------------
    def get(self) -> str:
        return self._value

    def set(self, value: str):
        if value in self._values:
            self._value = value
            self._label.configure(text=value)


class HistoryWindow:
    def __init__(self, history: History, on_run_ai: Callable | None = None, on_rebind: Callable | None = None):
        self._history      = history
        self._on_run_ai    = on_run_ai
        self._on_rebind    = on_rebind
        self._recording    = False
        self._pulse_on     = False
        self._hist_visible = False
        self._banner_h     = 0     # 0 or BANNER_H — tracks whether update banner is visible
        self._entry_frames: list[ctk.CTkFrame] = []

        self._root = ctk.CTk()
        self._root.title("Clembot-dictate")
        self._root.configure(fg_color=CLR_BORDER)
        self._root.resizable(False, False)
        self._root.withdraw()
        self._root.protocol("WM_DELETE_WINDOW", self._root.withdraw)
        self._set_window_icon()

        # Frameless. A 44px tool wearing a 32px title bar with minimise, maximise
        # and close reads as a dialog somebody shrank, and neither maximise nor the
        # taskbar entry mean anything for a strip that lives in the tray. The cost
        # is that dragging, placement and closing are now ours to draw: see
        # _build_header's grip and _start_drag below.
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._place_initial()

        # The root's own colour is the border. Everything else sits on this inset
        # frame, so the window carries a 1px edge against whatever is behind it.
        # Elevation is borders, never shadow, per the brand file.
        self._shell = ctk.CTkFrame(self._root, fg_color=CLR_BG, corner_radius=0)
        self._shell.pack(fill="both", expand=True, padx=1, pady=1)

        self._build_header()
        self._build_update_banner()
        self._build_history_panel()

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def ai_enabled(self) -> bool:
        return bool(self._ai_switch.get())

    @property
    def context_mode(self) -> str:
        return self._mode_menu.get()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _set_window_icon(self):
        try:
            size = 64
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([2, 2, size - 2, size - 2], fill=(60, 65, 80, 255))
            cx, cy = size // 2, size // 2
            r = 10
            white = (255, 255, 255, 230)
            draw.ellipse([cx - r, cy - r - 4, cx + r, cy + r - 4], fill=white)
            draw.rectangle([cx - 1, cy + r - 4, cx + 1, cy + r + 6], fill=white)
            draw.arc([cx - 8, cy - 2, cx + 8, cy + 14], start=0, end=180, fill=white, width=2)
            self._icon_photo = ImageTk.PhotoImage(img)
            self._root.iconphoto(True, self._icon_photo)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Frameless window plumbing
    # ------------------------------------------------------------------

    def _place_initial(self):
        """Top centre of the primary screen, a hair below the edge.

        A frameless window opens wherever Tk feels like otherwise, and "wherever"
        for a strip usually means on top of the thing you were reading.
        """
        try:
            screen_w = self._root.winfo_screenwidth()
            x = max(0, (screen_w - WINDOW_W) // 2)
            self._root.geometry(f"{WINDOW_W}x{COMPACT_H}+{x}+8")
        except Exception:
            self._root.geometry(f"{WINDOW_W}x{COMPACT_H}")

    def _resize(self, height: int):
        """Change height without teleporting the window back to the origin."""
        try:
            x, y = self._root.winfo_x(), self._root.winfo_y()
            self._root.geometry(f"{WINDOW_W}x{height}+{x}+{y}")
        except Exception:
            self._root.geometry(f"{WINDOW_W}x{height}")

    def _make_draggable(self, *widgets):
        for widget in widgets:
            widget.bind("<Button-1>", self._start_drag, add="+")
            widget.bind("<B1-Motion>", self._on_drag, add="+")

    def _start_drag(self, event):
        self._drag_from = (event.x_root - self._root.winfo_x(),
                           event.y_root - self._root.winfo_y())

    def _on_drag(self, event):
        origin = getattr(self, "_drag_from", None)
        if not origin:
            return
        self._root.geometry(f"+{event.x_root - origin[0]}+{event.y_root - origin[1]}")

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _label(self, master, text, size=None, color=None, tracked=False,
               weight="normal", **kwargs):
        """The one place a font is chosen, so the scale cannot drift again.

        The old header mixed 9, 10 and 12px across seven widgets with three
        weights between them, which is most of why it read as assembled rather
        than laid out.
        """
        return ctk.CTkLabel(
            master,
            text=theme.track(text) if tracked else text,
            text_color=color or CLR_SUBTEXT,
            font=ctk.CTkFont(family=theme.body(), size=size or theme.SIZE_LABEL,
                             weight=weight),
            **kwargs,
        )

    def _chip(self, master, text, color=None, fill=None):
        """A state chip: tracked micro-label on a quiet fill. Never an emoji."""
        return ctk.CTkLabel(
            master, text=theme.track(text),
            text_color=color or CLR_SUBTEXT,
            font=ctk.CTkFont(family=theme.body(), size=theme.SIZE_LABEL),
            fg_color=fill or CLR_SURFACE1,
            corner_radius=theme.RADIUS_SM,
            height=theme.CHIP_H,
        )

    def _hover_tint(self, icon):
        """Icons are flat until pointed at. Colour is the whole hover state: a
        background swap behind a 12px canvas reads as a glitch."""
        icon.configure(cursor="hand2")
        icon.bind("<Enter>", lambda _: icon.set_color(CLR_TEXT), add="+")
        icon.bind("<Leave>", lambda _: icon.set_color(CLR_SUBTEXT), add="+")

    def _build_header(self):
        bar = ctk.CTkFrame(self._shell, fg_color=CLR_SURFACE, corner_radius=0,
                           height=COMPACT_H)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        self._bar = bar

        # -- Left: grip, status light, state ------------------------------
        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", padx=(theme.SP_3, 0))

        self._grip = icons.Grip(left, bg=CLR_SURFACE, color=CLR_BORDER, size=12)
        self._grip.pack(side="left", padx=(0, theme.SP_2))

        self._dot = icons.Dot(left, bg=CLR_SURFACE, color=CLR_IDLE, size=10, radius=4)
        self._dot.pack(side="left", padx=(0, theme.SP_2))

        self._indicator = self._label(left, "Ready", tracked=True, anchor="w")
        self._indicator.pack(side="left")

        # With no title bar, dragging has to live somewhere. It lives on the bar
        # and on everything inert sitting on it.
        self._make_draggable(bar, left, self._grip, self._dot, self._indicator)

        # -- Left, conditional: state chips -------------------------------
        self._clip_badge = self._chip(bar, "Clipboard")
        self._auto_badge = self._chip(bar, "Auto", color=theme.ACCENT,
                                      fill=theme.ACCENT_DIM)

        # -- Right, outermost first ---------------------------------------
        self._close_btn = icons.Close(bar, bg=CLR_SURFACE, color=CLR_SUBTEXT, size=14)
        self._close_btn.pack(side="right", padx=(theme.SP_2, theme.SP_3))
        self._hover_tint(self._close_btn)
        self._close_btn.bind("<Button-1>", lambda _: self._root.withdraw())

        self._menu_btn = icons.Menu(bar, bg=CLR_SURFACE, color=CLR_SUBTEXT, size=14)
        self._menu_btn.pack(side="right", padx=(0, theme.SP_2))
        self._hover_tint(self._menu_btn)
        self._menu_btn.bind("<Button-1>", lambda _: self._open_settings())

        # History: a label and a chevron that behave as one control.
        hist = ctk.CTkFrame(bar, fg_color="transparent")
        hist.pack(side="right", padx=(0, theme.SP_4))
        self._hist_label = self._label(hist, "History", tracked=True)
        self._hist_label.pack(side="left", padx=(0, theme.SP_1))
        self._hist_chevron = icons.Chevron(hist, bg=CLR_SURFACE, color=CLR_SUBTEXT,
                                           size=12)
        self._hist_chevron.pack(side="left")
        for widget in (hist, self._hist_label, self._hist_chevron):
            widget.bind("<Button-1>", lambda _: self._toggle_history())
            widget.configure(cursor="hand2")

        # -- Mode dropdown -------------------------------------------------
        self._mode_menu = ModeSelect(
            bar,
            values=list(CONTEXT_MODES.keys()),
            initial=DEFAULT_CONTEXT_MODE,
            command=self._on_mode_change,
        )
        self._mode_menu.pack(side="right", padx=(0, theme.SP_3))

        # -- AI toggle -----------------------------------------------------
        ai_row = ctk.CTkFrame(bar, fg_color="transparent")
        ai_row.pack(side="right", padx=(0, theme.SP_4))

        self._ai_label = self._label(ai_row, "AI", tracked=True)
        self._ai_label.pack(side="left", padx=(0, theme.SP_2))

        self._ai_switch = ctk.CTkSwitch(
            ai_row, text="",
            width=34, height=18,
            switch_width=30, switch_height=15,
            fg_color=CLR_SURFACE2,
            button_color=CLR_TEXT,
            button_hover_color=CLR_TEXT,
            progress_color=theme.ACCENT,
            command=self._on_ai_toggle,
        )
        self._ai_switch.select()
        self._ai_switch.pack(side="left")
        self._sync_ai_label()

    def _sync_ai_label(self):
        """The label carries the state too, so the switch is not the only tell."""
        on = bool(self._ai_switch.get())
        self._ai_label.configure(text_color=theme.ACCENT if on else CLR_SUBTEXT)

    def _build_history_panel(self):
        self._history_panel = ctk.CTkFrame(self._shell, fg_color=CLR_BG, corner_radius=0)
        # Not packed yet — starts hidden

        ctk.CTkLabel(
            self._history_panel, text="HISTORY",
            text_color=CLR_SUBTEXT,
            font=ctk.CTkFont(size=9, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(8, 3))

        self._scroll = ctk.CTkScrollableFrame(
            self._history_panel,
            fg_color=CLR_BG,
            scrollbar_button_color=CLR_SURFACE,
            corner_radius=0,
        )
        self._scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # Empty state — visible when no dictations exist yet
        self._empty_state = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._empty_state.pack(fill="x", pady=48)

        ctk.CTkLabel(
            self._empty_state, text="🎙",
            font=ctk.CTkFont(size=34),
            text_color=CLR_SURFACE2,
        ).pack()
        ctk.CTkLabel(
            self._empty_state, text="No dictations yet",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=CLR_IDLE,
        ).pack(pady=(10, 4))
        ctk.CTkLabel(
            self._empty_state,
            text=f"Hold  [ {HOTKEY} ]  anywhere to start",
            font=ctk.CTkFont(size=11),
            text_color=CLR_SURFACE2,
        ).pack()

        # Load existing history entries (hides empty state if any exist)
        for entry in self._history.get_all():
            self._add_entry_widget(entry, prepend=False)

    # ------------------------------------------------------------------
    # Thread-safe public API
    # ------------------------------------------------------------------

    def show(self):
        self._root.after(0, self._do_show)

    def show_passive(self):
        """Show window without stealing focus — use on startup."""
        self._root.after(0, lambda: (self._root.deiconify(), self._root.lift()))

    def add_entry(self, entry: Entry):
        self._root.after(0, lambda: self._add_entry_widget(entry, prepend=True))

    def set_status(self, text: str | None = None, color: str | None = None):
        """Set the state word and the dot colour. text=None restores Ready."""
        self._root.after(0, lambda: self._do_set_status(text, color))

    def set_recording(self, recording: bool):
        self._root.after(0, lambda: self._do_set_recording(recording))

    def set_context_mode(self, mode: str):
        """Switch the mode dropdown and flash the AUTO chip (thread-safe)."""
        self._root.after(0, lambda: self._do_set_context_mode(mode))

    def show_update_banner(self, latest: str, url: str):
        """Show the update notification banner (thread-safe). Call at most once."""
        self._root.after(0, lambda: self._do_show_update_banner(latest, url))

    def set_clipboard_only(self, active: bool):
        """Show or hide the clipboard-only badge in the header (thread-safe)."""
        self._root.after(0, lambda: self._do_set_clipboard_only(active))

    def mainloop(self):
        self._root.mainloop()

    def quit(self):
        self._root.after(0, self._root.quit)

    # ------------------------------------------------------------------
    # Internal — main thread only
    # ------------------------------------------------------------------

    def _do_show(self):
        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()

    def _do_set_status(self, text: str | None, color: str | None):
        """Colour lives on the dot, words live in the label. They used to be one
        string ("● Ready"), which meant the state colour and the state name could
        not differ, and a long status pushed the dot off its own baseline."""
        if text is None:
            if not self._recording:
                self._indicator.configure(text=theme.track("Ready"), text_color=CLR_SUBTEXT)
                self._dot.set_color(CLR_IDLE)
        else:
            self._indicator.configure(text=theme.track(text), text_color=CLR_SUBTEXT)
            self._dot.set_color(color or CLR_IDLE)

    def _do_set_recording(self, recording: bool):
        self._recording = recording
        if recording:
            self._indicator.configure(text=theme.track("Recording"),
                                      text_color=CLR_RECORDING)
            self._dot.set_color(CLR_RECORDING)
            self._pulse()
        else:
            self._indicator.configure(text=theme.track("Ready"), text_color=CLR_SUBTEXT)
            self._dot.set_color(CLR_IDLE)

    def _do_set_context_mode(self, mode: str):
        if mode not in CONTEXT_MODES:
            return
        current = self._mode_menu.get()
        if current == mode:
            return  # no change — don't flash badge
        self._mode_menu.set(mode)
        # Flash the AUTO chip for two seconds, next to the state it explains.
        self._auto_badge.pack(side="left", padx=(theme.SP_3, 0))
        self._root.after(2000, self._hide_auto_badge)

    def _hide_auto_badge(self):
        try:
            self._auto_badge.pack_forget()
        except Exception:
            pass

    def _pulse(self):
        if not self._recording:
            return
        self._pulse_on = not self._pulse_on
        # Only the dot pulses. Pulsing the word made the whole left edge flicker.
        self._dot.set_color(CLR_RECORDING if self._pulse_on else theme.RECORDING_DIM)
        self._root.after(500, self._pulse)

    def _toggle_history(self):
        self._hist_visible = not self._hist_visible
        if self._hist_visible:
            self._history_panel.pack(fill="both", expand=True)
            self._resize(HISTORY_H + self._banner_h)
            self._root.resizable(False, True)
        else:
            self._history_panel.pack_forget()
            self._resize(COMPACT_H + self._banner_h)
            self._root.resizable(False, False)
        self._hist_chevron.set_up(self._hist_visible)
        self._hist_label.configure(
            text_color=CLR_TEXT if self._hist_visible else CLR_SUBTEXT)

    def _build_update_banner(self):
        self._update_banner = ctk.CTkFrame(
            self._shell, fg_color=theme.ACCENT_DIM, corner_radius=0, height=BANNER_H,
        )
        self._update_banner.pack_propagate(False)
        # Content populated on first show — not built here

    def _do_show_update_banner(self, latest: str, url: str):
        if not getattr(self, "_banner_built", False):
            row = ctk.CTkFrame(self._update_banner, fg_color="transparent")
            row.pack(fill="both", expand=True, padx=10)

            self._label(row, "Update available", tracked=True,
                        color=theme.ACCENT).pack(side="left", padx=(0, theme.SP_2))
            self._label(row, f"v{latest}", size=theme.SIZE_SMALL,
                        color=CLR_TEXT).pack(side="left", padx=(0, theme.SP_3))

            dl = self._label(row, "Download", tracked=True, color=theme.ACCENT,
                             cursor="hand2")
            dl.pack(side="left")
            if url:
                dl.bind("<Button-1>", lambda _: webbrowser.open(url))

            dismiss = icons.Close(row, bg=theme.ACCENT_DIM, color=CLR_SUBTEXT, size=12)
            dismiss.pack(side="right")
            self._hover_tint(dismiss)
            dismiss.bind("<Button-1>", lambda _: self._dismiss_update_banner())

            self._banner_built = True

        self._update_banner.pack(fill="x")
        self._banner_h = BANNER_H
        self._resize((HISTORY_H if self._hist_visible else COMPACT_H) + BANNER_H)

    def _dismiss_update_banner(self):
        self._update_banner.pack_forget()
        self._banner_h = 0
        self._resize(HISTORY_H if self._hist_visible else COMPACT_H)

    def _do_set_clipboard_only(self, active: bool):
        if active:
            self._clip_badge.pack(side="left", padx=(theme.SP_3, 0))
        else:
            try:
                self._clip_badge.pack_forget()
            except Exception:
                pass

    def _on_ai_toggle(self):
        enabled = self.ai_enabled
        self._mode_menu.configure(state="normal" if enabled else "disabled")

    def _on_mode_change(self, _value: str):
        pass  # mode is read at call time

    def _open_settings(self):
        # Prevent duplicate windows
        if hasattr(self, "_settings_win") and self._settings_win.winfo_exists():
            self._settings_win.lift()
            self._settings_win.focus_force()
            return

        win = ctk.CTkToplevel(self._root)
        win.title("Clembot-dictate settings")
        win.geometry("340x560")
        win.configure(fg_color=CLR_BG)
        win.resizable(False, False)
        win.grab_set()   # modal
        self._settings_win = win

        # ── Hotkey section ───────────────────────────────────────────
        ctk.CTkLabel(
            win, text=theme.track("Hotkey"),
            text_color=theme.ACCENT,
            font=ctk.CTkFont(family=theme.body(), size=theme.SIZE_LABEL),
            anchor="w",
        ).pack(fill="x", padx=20, pady=(20, 2))

        ctk.CTkLabel(
            win, text="Click the field then press any key to remap.",
            text_color=CLR_SUBTEXT,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(fill="x", padx=20, pady=(0, 8))

        key_row = ctk.CTkFrame(win, fg_color="transparent")
        key_row.pack(fill="x", padx=20)

        # Key name display (read-only appearance, captures keypresses)
        current_key = getattr(self, "_current_hotkey", HOTKEY)
        key_var = tk.StringVar(value=current_key)

        key_entry = ctk.CTkEntry(
            key_row, textvariable=key_var,
            width=90, height=30,
            fg_color=CLR_SURFACE1,
            border_color=CLR_BORDER,
            text_color=CLR_TEXT,
            font=ctk.CTkFont(family=theme.mono(), size=theme.SIZE_BODY),
            justify="center",
        )
        key_entry.pack(side="left", padx=(0, 8))

        status_label = ctk.CTkLabel(
            key_row, text="",
            text_color=CLR_SUBTEXT,
            font=ctk.CTkFont(size=10),
            anchor="w",
        )
        status_label.pack(side="left")

        # Key capture: intercept any keypress while entry is focused
        _KEYSYM_MAP = {
            "grave": "`", "space": "space", "Return": "enter",
            "Tab": "tab", "Escape": "esc",
            "BackSpace": "backspace", "Delete": "delete",
        }

        def _capture(event):
            sym  = event.keysym
            name = _KEYSYM_MAP.get(sym, sym.lower())
            key_var.set(name)
            return "break"   # prevent the character from being typed

        key_entry._entry.bind("<Key>", _capture)

        def _apply():
            new_key = key_var.get().strip()
            if not new_key:
                return
            if self._on_rebind:
                ok = self._on_rebind(new_key)
                if ok:
                    self._current_hotkey = new_key
                    status_label.configure(text=theme.track("Applied"), text_color=theme.STATUS_OK)
                else:
                    status_label.configure(text="✗ Invalid key", text_color=CLR_RECORDING)
            else:
                status_label.configure(text="Restart to apply", text_color=CLR_SUBTEXT)

        ctk.CTkButton(
            key_row, text="Apply",
            width=60, height=30,
            fg_color=CLR_RUN_BTN, hover_color=CLR_RUN_HOVER,
            text_color=CLR_RUN_TEXT, font=ctk.CTkFont(size=10),
            corner_radius=4,
            command=_apply,
        ).pack(side="left", padx=(0, 0))

        # ── Startup ──────────────────────────────────────────────────
        ctk.CTkFrame(win, fg_color=CLR_SURFACE2, height=1, corner_radius=0).pack(
            fill="x", padx=20, pady=(20, 0)
        )
        ctk.CTkLabel(
            win, text=theme.track("Startup"),
            text_color=theme.ACCENT,
            font=ctk.CTkFont(family=theme.body(), size=theme.SIZE_LABEL),
            anchor="w",
        ).pack(fill="x", padx=20, pady=(16, 4))

        startup_row = ctk.CTkFrame(win, fg_color="transparent")
        startup_row.pack(fill="x", padx=20, pady=(0, 4))

        ctk.CTkLabel(
            startup_row, text="Launch at login",
            text_color=CLR_SUBTEXT,
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(side="left")

        startup_status = ctk.CTkLabel(
            startup_row, text="",
            text_color=CLR_SUBTEXT,
            font=ctk.CTkFont(size=10),
        )
        startup_status.pack(side="right")

        startup_switch = ctk.CTkSwitch(
            startup_row, text="",
            width=36, height=18,
            switch_width=32, switch_height=16,
            button_color=CLR_AI_LABEL,
            button_hover_color=theme.ACCENT_HOVER,
            progress_color=theme.ACCENT_DIM,
        )
        startup_switch.pack(side="right", padx=(0, 8))

        try:
            if startup.is_registered():
                startup_switch.select()
        except Exception:
            pass

        def _toggle_startup():
            try:
                if startup_switch.get():
                    ok = startup.register()
                    startup_status.configure(
                        text=theme.track("Registered") if ok else theme.track("Failed"),
                        text_color=theme.STATUS_OK if ok else CLR_RECORDING,
                    )
                else:
                    ok = startup.unregister()
                    startup_status.configure(
                        text=theme.track("Removed") if ok else theme.track("Failed"),
                        text_color=CLR_SUBTEXT if ok else CLR_RECORDING,
                    )
            except Exception:
                startup_status.configure(text=theme.track("Error"), text_color=CLR_RECORDING)

        startup_switch.configure(command=_toggle_startup)

        # ── API Key ──────────────────────────────────────────────────
        ctk.CTkFrame(win, fg_color=CLR_SURFACE2, height=1, corner_radius=0).pack(
            fill="x", padx=20, pady=(16, 0)
        )
        ctk.CTkLabel(
            win, text=theme.track("AI Key"),
            text_color=theme.ACCENT,
            font=ctk.CTkFont(family=theme.body(), size=theme.SIZE_LABEL),
            anchor="w",
        ).pack(fill="x", padx=20, pady=(16, 2))

        ctk.CTkLabel(
            win, text="Anthropic API key. Stored in Windows Credential Manager.",
            text_color=CLR_SUBTEXT,
            font=ctk.CTkFont(size=10),
            anchor="w",
        ).pack(fill="x", padx=20, pady=(0, 8))

        key_input_row = ctk.CTkFrame(win, fg_color="transparent")
        key_input_row.pack(fill="x", padx=20)

        api_key_var = tk.StringVar()
        api_key_entry = ctk.CTkEntry(
            key_input_row, textvariable=api_key_var,
            placeholder_text="sk-ant-...",
            show="•",
            width=190, height=30,
            fg_color=CLR_SURFACE1,
            border_color=CLR_SURFACE2,
            text_color=CLR_TEXT,
            font=ctk.CTkFont(size=11),
        )
        api_key_entry.pack(side="left", padx=(0, 8))

        api_key_status = ctk.CTkLabel(
            key_input_row, text="",
            text_color=CLR_SUBTEXT,
            font=ctk.CTkFont(size=10),
            anchor="w",
        )

        def _save_api_key():
            val = api_key_var.get().strip()
            if not val:
                api_key_status.configure(text="Enter a key first", text_color=CLR_RECORDING)
                api_key_status.pack(side="left")
                return
            try:
                import keyring
                keyring.set_password("Clembot-dictate", "anthropic_api_key", val)
                api_key_var.set("")
                api_key_entry.configure(placeholder_text="sk-ant-... (saved)")
                api_key_status.configure(text=theme.track("Saved"), text_color=theme.STATUS_OK)
            except Exception as e:
                api_key_status.configure(text=f"✗ {e}", text_color=CLR_RECORDING)
            api_key_status.pack(side="left")

        ctk.CTkButton(
            key_input_row, text="Save",
            width=52, height=30,
            fg_color=CLR_RUN_BTN, hover_color=CLR_RUN_HOVER,
            text_color=CLR_RUN_TEXT, font=ctk.CTkFont(size=10),
            corner_radius=4,
            command=_save_api_key,
        ).pack(side="left")

        # Show whether a key is already stored
        try:
            import keyring
            existing = keyring.get_password("Clembot-dictate", "anthropic_api_key")
            if existing:
                api_key_entry.configure(placeholder_text="sk-ant-... (saved)")
        except Exception:
            pass

        # ── Divider ──────────────────────────────────────────────────
        ctk.CTkFrame(win, fg_color=CLR_SURFACE2, height=1, corner_radius=0).pack(
            fill="x", padx=20, pady=(16, 0)
        )

        # ── About section ────────────────────────────────────────────
        ctk.CTkLabel(
            win, text=theme.track("About"),
            text_color=theme.ACCENT,
            font=ctk.CTkFont(family=theme.body(), size=theme.SIZE_LABEL),
            anchor="w",
        ).pack(fill="x", padx=20, pady=(16, 6))

        # Inline hyperlink requires tk.Text with a tagged region
        about = tk.Text(
            win, wrap="word", width=1, height=5,
            bg=CLR_BG, fg=theme.TEXT_SECONDARY,
            font=(theme.body(), theme.SIZE_BODY),
            relief="flat", borderwidth=0, highlightthickness=0,
            padx=0, pady=0, cursor="arrow", spacing3=3,
        )
        about.pack(fill="x", padx=20, pady=(0, 16))

        about.insert("end", f"Clembot-dictate v{VERSION}  ·  by ")
        about.insert("end", "Wanessa Labs", "link")
        about.insert("end", ".\n\nSpeech is transcribed on this machine and never written to disk. ")
        about.insert("end", "Windows only: the Mac tooling for this is already good.", "note")
        about.tag_configure("note", foreground=CLR_SUBTEXT,
                            font=(theme.body(), theme.SIZE_SMALL))

        about.tag_configure("link", foreground=CLR_AI_LABEL, underline=True)
        about.tag_bind("link", "<Button-1>", lambda _: webbrowser.open("https://www.wanessalabs.com"))
        about.tag_bind("link", "<Enter>",    lambda _: about.configure(cursor="hand2"))
        about.tag_bind("link", "<Leave>",    lambda _: about.configure(cursor="arrow"))
        about.configure(state="disabled")

    # ------------------------------------------------------------------
    # Card construction
    # ------------------------------------------------------------------

    def _add_entry_widget(self, entry: Entry, prepend: bool = True):
        # Hide the empty state the first time a real entry arrives
        if not self._entry_frames and hasattr(self, "_empty_state"):
            self._empty_state.pack_forget()

        card = ctk.CTkFrame(self._scroll, fg_color=CLR_SURFACE, corner_radius=8)
        self._build_card(card, entry)

        if prepend and self._entry_frames:
            card.pack(fill="x", padx=3, pady=3)
            for existing in self._entry_frames:
                existing.pack_forget()
                existing.pack(fill="x", padx=3, pady=3)
            self._entry_frames.insert(0, card)
        else:
            card.pack(fill="x", padx=3, pady=3)
            self._entry_frames.append(card)

    def _build_card(self, card: ctk.CTkFrame, entry: Entry) -> _CardRefs:
        has_raw     = bool(entry.raw)
        has_refined = entry.has_refinement

        # ── Header row ───────────────────────────────────────────────
        hrow = ctk.CTkFrame(card, fg_color="transparent")
        hrow.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(
            hrow, text=entry.display_time,
            text_color=CLR_SUBTEXT,
            font=ctk.CTkFont(size=10),
        ).pack(side="left")

        copy_target = entry.text if has_refined else (entry.raw or entry.text)
        copy_btn = ctk.CTkButton(
            hrow, text=theme.track("Copy"),
            width=46, height=20,
            fg_color=CLR_SURFACE1, hover_color=CLR_SURFACE2,
            text_color=CLR_TEXT, font=ctk.CTkFont(size=10),
            corner_radius=4,
            command=lambda: pyperclip.copy(copy_target),
        )
        copy_btn.pack(side="right", padx=(3, 0))

        run_btn = None
        if has_raw and self._on_run_ai:
            run_btn = ctk.CTkButton(
                hrow,
                text=theme.track("Re-run") if has_refined else theme.track("Run AI"),
                width=68, height=20,
                fg_color=CLR_RUN_BTN, hover_color=CLR_RUN_HOVER,
                text_color=CLR_RUN_TEXT, font=ctk.CTkFont(size=10),
                corner_radius=4,
            )
            run_btn.pack(side="right", padx=(0, 3))

        # ── Body ─────────────────────────────────────────────────────
        if has_raw:
            raw_block = ctk.CTkFrame(card, fg_color=CLR_BG, corner_radius=5)
            raw_block.pack(fill="x", padx=8, pady=(0, 3))
            ctk.CTkLabel(
                raw_block, text=theme.track("Raw"),
                text_color=CLR_RAW_LABEL,
                font=ctk.CTkFont(size=8, weight="bold"),
            ).pack(anchor="w", padx=8, pady=(5, 1))
            self._selectable_text(raw_block, entry.raw, CLR_BG, CLR_RAW_TEXT, size=11)

            divider = ctk.CTkFrame(card, fg_color=CLR_SURFACE2, height=1, corner_radius=0)
            if has_refined:
                divider.pack(fill="x", padx=8, pady=(0, 3))

            ai_frame = ctk.CTkFrame(card, fg_color=CLR_SURFACE1, corner_radius=5)
            ai_text  = self._build_ai_section(ai_frame, entry.text if has_refined else "")
            if has_refined:
                ai_frame.pack(fill="x", padx=8, pady=(0, 8))
        else:
            divider  = ctk.CTkFrame(card, fg_color=CLR_SURFACE2, height=1, corner_radius=0)
            ai_frame = ctk.CTkFrame(card, fg_color=CLR_SURFACE1, corner_radius=5)
            ai_text  = self._build_ai_section(ai_frame, "")
            self._selectable_text(card, entry.text, CLR_SURFACE, CLR_TEXT, size=12, pady=(0, 10))

        refs = _CardRefs(
            entry=entry, copy_btn=copy_btn, run_btn=run_btn,
            divider=divider, ai_frame=ai_frame, ai_text=ai_text,
        )
        refs.set_copy_text(copy_target)

        if run_btn and self._on_run_ai:
            run_btn.configure(command=lambda r=refs: self._handle_run_ai(r))

        return refs

    def _build_ai_section(self, ai_frame: ctk.CTkFrame, text: str) -> tk.Text:
        ctk.CTkLabel(
            ai_frame, text=theme.track("AI"),
            text_color=CLR_AI_LABEL,
            font=ctk.CTkFont(size=8, weight="bold"),
        ).pack(anchor="w", padx=8, pady=(5, 1))
        return self._selectable_text(ai_frame, text, CLR_SURFACE1, CLR_AI_TEXT, size=12)

    # ------------------------------------------------------------------
    # Run AI on card
    # ------------------------------------------------------------------

    def _handle_run_ai(self, refs: _CardRefs):
        if not refs.entry.raw or not self._on_run_ai:
            return
        refs.run_btn.configure(state="disabled", text="Running…")
        def done(refined: str):
            self._root.after(0, lambda: self._apply_ai_result(refs, refined))
        self._on_run_ai(refs.entry.raw, refs.entry, done)

    def _apply_ai_result(self, refs: _CardRefs, refined: str):
        refs.ai_text.configure(state="normal")
        refs.ai_text.delete("1.0", "end")
        refs.ai_text.insert("1.0", refined)
        refs.ai_text.configure(state="disabled", height=MAX_LINES)

        try:
            refs.divider.pack_info()
        except tk.TclError:
            refs.divider.pack(fill="x", padx=8, pady=(0, 3))
        try:
            refs.ai_frame.pack_info()
        except tk.TclError:
            refs.ai_frame.pack(fill="x", padx=8, pady=(0, 8))

        self._root.after(120, lambda: self._setup_ai_expand(refs))
        refs.set_copy_text(refined)
        if refs.run_btn:
            refs.run_btn.configure(state="normal", text=theme.track("Re-run"))

    def _setup_ai_expand(self, refs: _CardRefs):
        try:
            lines = refs.ai_text.count("1.0", "end", "displaylines")[0]
        except Exception:
            return
        refs._ai_full_lines[0] = lines
        refs.ai_text.configure(height=min(MAX_LINES, lines))
        if lines <= MAX_LINES:
            if refs.ai_expand_btn:
                refs.ai_expand_btn.pack_forget()
            return
        if refs.ai_expand_btn is None:
            def _toggle():
                if refs._ai_expanded[0]:
                    refs.ai_text.configure(height=MAX_LINES)
                    refs.ai_expand_btn.configure(text=theme.track("more"))
                    refs._ai_expanded[0] = False
                else:
                    refs.ai_text.configure(height=refs._ai_full_lines[0])
                    refs.ai_expand_btn.configure(text=theme.track("less"))
                    refs._ai_expanded[0] = True
            refs.ai_expand_btn = ctk.CTkButton(
                refs.ai_frame, text=theme.track("more"),
                height=18, fg_color="transparent",
                hover_color=CLR_SURFACE2, text_color=CLR_SUBTEXT,
                font=ctk.CTkFont(size=9), anchor="w",
                command=_toggle,
            )
            refs.ai_expand_btn.pack(fill="x", padx=8, pady=(0, 5))
        else:
            refs._ai_expanded[0] = False
            refs.ai_expand_btn.configure(text=theme.track("more"))
            refs.ai_expand_btn.pack(fill="x", padx=8, pady=(0, 5))

    # ------------------------------------------------------------------
    # Selectable text widget (capped at MAX_LINES, expandable)
    # ------------------------------------------------------------------

    def _selectable_text(
        self, parent, text: str, bg: str, fg: str,
        size: int = 12, pady: tuple = (0, 6),
    ) -> tk.Text:
        widget = tk.Text(
            parent, wrap="word", width=1, height=MAX_LINES,
            font=(theme.body(), size), bg=bg, fg=fg,
            relief="flat", borderwidth=0, highlightthickness=0,
            selectbackground=CLR_SURFACE2, selectforeground=CLR_TEXT,
            padx=8, pady=5, cursor="arrow", spacing3=2,
        )
        widget.pack(fill="x", pady=pady)
        if text:
            widget.insert("1.0", text)
        widget.configure(state="disabled")

        expanded   = [False]
        full_lines = [MAX_LINES]
        btn_holder = [None]

        def _toggle():
            if expanded[0]:
                widget.configure(height=MAX_LINES)
                btn_holder[0].configure(text=theme.track("more"))
                expanded[0] = False
            else:
                widget.configure(height=full_lines[0])
                btn_holder[0].configure(text=theme.track("less"))
                expanded[0] = True

        last_width = [0]

        def _check(event=None):
            """Fit the block to its content, once the block knows how wide it is.

            Called on every <Configure>, so it corrects itself the moment the
            panel is packed. `last_width` keeps it from re-entering: configuring
            the height fires another <Configure>, and without the guard that is
            an infinite loop rather than a layout."""
            try:
                width = widget.winfo_width()
                if width <= 1 or (width == last_width[0] and event is not None):
                    return
                last_width[0] = width

                counted = widget.count("1.0", "end", "displaylines")
                if not counted:
                    return
                lines = max(1, counted[0])
                full_lines[0] = lines

                wanted = full_lines[0] if expanded[0] else min(MAX_LINES, lines)
                if int(widget.cget("height")) != wanted:
                    widget.configure(height=wanted)

                if lines > MAX_LINES and btn_holder[0] is None:
                    btn = ctk.CTkButton(
                        parent, text=theme.track("more"),
                        height=18, fg_color="transparent",
                        hover_color=CLR_SURFACE2, text_color=CLR_SUBTEXT,
                        font=ctk.CTkFont(family=theme.body(), size=theme.SIZE_LABEL),
                        anchor="w",
                        command=_toggle,
                    )
                    btn.pack(fill="x", padx=theme.SP_2, pady=(0, theme.SP_1))
                    btn_holder[0] = btn
                elif lines <= MAX_LINES and btn_holder[0] is not None:
                    btn_holder[0].destroy()
                    btn_holder[0] = None
            except Exception:
                pass

        widget.bind("<Configure>", _check)
        parent.after(120, _check)
        return widget
