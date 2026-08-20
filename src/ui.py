"""
Clembot-dictate — UI
Single-row header strip. History panel toggles open/closed.

Compact (history hidden):
  ┌────────────────────────────────────────────────────────┐
  │  ● Ready    AI ●━━  [Claude Code ▼]    [▼ History]    │
  └────────────────────────────────────────────────────────┘

Expanded (history shown):
  ┌────────────────────────────────────────────────────────┐
  │  ● Ready    AI ●━━  [Claude Code ▼]    [▲ History]    │
  ├────────────────────────────────────────────────────────┤
  │  14:23            [✦ Run AI]  [Copy]                   │
  │  ┌ RAW ──────────────────────────────────────────────┐ │
  │  │ um so basically...                    ▼ Show more │ │
  │  └────────────────────────────────────────────────── ┘ │
  │  ┌ ✦ AI ─────────────────────────────────────────── ┐  │
  │  │ Fix the bug in auth.                  ▼ Show more│  │
  │  └────────────────────────────────────────────────── ┘  │
  └────────────────────────────────────────────────────────┘

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

from history import History, Entry
from config import CONTEXT_MODES, DEFAULT_CONTEXT_MODE, HOTKEY, AUTO_CONTEXT, VERSION
import startup

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Catppuccin Mocha
CLR_BG        = "#1e1e2e"
CLR_SURFACE   = "#2a2a3e"
CLR_SURFACE1  = "#313244"
CLR_SURFACE2  = "#45475a"
CLR_TEXT      = "#cdd6f4"
CLR_SUBTEXT   = "#6c7086"
CLR_IDLE      = "#585b70"
CLR_RECORDING = "#f38ba8"
CLR_RAW_LABEL = "#a6adc8"
CLR_RAW_TEXT  = "#7f849c"
CLR_AI_LABEL  = "#89dceb"
CLR_AI_TEXT   = "#cdd6f4"
CLR_RUN_BTN   = "#1e3a4a"
CLR_RUN_HOVER = "#2a4f64"
CLR_RUN_TEXT  = "#89dceb"

WINDOW_W   = 500
COMPACT_H  = 52    # header only
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
        self._root.geometry(f"{WINDOW_W}x{COMPACT_H}")
        self._root.configure(fg_color=CLR_BG)
        self._root.resizable(False, False)
        self._root.withdraw()
        self._root.protocol("WM_DELETE_WINDOW", self._root.withdraw)
        self._set_window_icon()

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

    def _build_header(self):
        bar = ctk.CTkFrame(self._root, fg_color=CLR_SURFACE, corner_radius=0, height=COMPACT_H)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # ── Status indicator (left) ──────────────────────────────────
        self._indicator = ctk.CTkLabel(
            bar, text="● Ready",
            text_color=CLR_IDLE,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=90, anchor="w",
        )
        self._indicator.pack(side="left", padx=(12, 0))

        # ── Clipboard-only badge (hidden until tray toggle is on) ────
        self._clip_badge = ctk.CTkLabel(
            bar, text="📋 clip",
            text_color=CLR_SUBTEXT,
            font=ctk.CTkFont(size=9),
            fg_color=CLR_SURFACE1,
            corner_radius=4,
            width=48, height=18,
        )
        # Starts hidden — packed by set_clipboard_only(True)

        # ── History toggle (far right) ───────────────────────────────
        self._hist_btn = ctk.CTkButton(
            bar, text="▼ History",
            width=84, height=26,
            fg_color=CLR_SURFACE1, hover_color=CLR_SURFACE2,
            text_color=CLR_SUBTEXT, font=ctk.CTkFont(size=10),
            corner_radius=4,
            command=self._toggle_history,
        )
        self._hist_btn.pack(side="right", padx=(0, 10))

        # ── Settings button ──────────────────────────────────────────
        ctk.CTkButton(
            bar, text="⚙",
            width=28, height=26,
            fg_color=CLR_SURFACE1, hover_color=CLR_SURFACE2,
            text_color=CLR_SUBTEXT, font=ctk.CTkFont(size=12),
            corner_radius=4,
            command=self._open_settings,
        ).pack(side="right", padx=(0, 4))

        # ── Auto-context badge (shown briefly after auto-switch) ─────
        self._auto_badge = ctk.CTkLabel(
            bar, text="⟳ auto",
            text_color=CLR_AI_LABEL,
            font=ctk.CTkFont(size=9),
            fg_color=CLR_RUN_BTN,
            corner_radius=4,
            width=48, height=18,
        )
        # Starts hidden — packed temporarily on auto-context switch

        # ── Mode dropdown (right of center) ─────────────────────────
        self._mode_menu = ctk.CTkOptionMenu(
            bar,
            values=list(CONTEXT_MODES.keys()),
            variable=tk.StringVar(value=DEFAULT_CONTEXT_MODE),
            width=130, height=26,
            fg_color=CLR_SURFACE1,
            button_color=CLR_SURFACE1,
            button_hover_color=CLR_SURFACE2,
            dropdown_fg_color=CLR_SURFACE,
            dropdown_hover_color=CLR_SURFACE2,
            text_color=CLR_AI_LABEL,
            dropdown_text_color=CLR_TEXT,
            font=ctk.CTkFont(size=10),
            dropdown_font=ctk.CTkFont(size=11),
            corner_radius=4,
            command=self._on_mode_change,
        )
        self._mode_menu.pack(side="right", padx=(0, 6))

        # ── AI toggle ───────────────────────────────────────────────
        ai_row = ctk.CTkFrame(bar, fg_color="transparent")
        ai_row.pack(side="right", padx=(0, 8))

        ctk.CTkLabel(
            ai_row, text="AI",
            text_color=CLR_AI_LABEL,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).pack(side="left", padx=(0, 3))

        self._ai_switch = ctk.CTkSwitch(
            ai_row, text="",
            width=36, height=18,
            switch_width=32, switch_height=16,
            button_color=CLR_AI_LABEL,
            button_hover_color="#6bcfde",
            progress_color="#1e3a4a",
            command=self._on_ai_toggle,
        )
        self._ai_switch.select()
        self._ai_switch.pack(side="left")

    def _build_history_panel(self):
        self._history_panel = ctk.CTkFrame(self._root, fg_color=CLR_BG, corner_radius=0)
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
        """Set indicator to custom text. Pass text=None to restore '● Ready'."""
        self._root.after(0, lambda: self._do_set_status(text, color))

    def set_recording(self, recording: bool):
        self._root.after(0, lambda: self._do_set_recording(recording))

    def set_context_mode(self, mode: str):
        """Switch the mode dropdown and flash the ⟳ auto badge (thread-safe)."""
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
        if text is None:
            if not self._recording:
                self._indicator.configure(text="● Ready", text_color=CLR_IDLE)
        else:
            self._indicator.configure(text=text, text_color=color or CLR_SUBTEXT)

    def _do_set_recording(self, recording: bool):
        self._recording = recording
        if recording:
            self._indicator.configure(text="● Rec", text_color=CLR_RECORDING)
            self._pulse()
        else:
            self._indicator.configure(text="● Ready", text_color=CLR_IDLE)

    def _do_set_context_mode(self, mode: str):
        if mode not in CONTEXT_MODES:
            return
        current = self._mode_menu.get()
        if current == mode:
            return  # no change — don't flash badge
        self._mode_menu.set(mode)
        # Flash the ⟳ auto badge for 2 seconds
        self._auto_badge.pack(side="right", padx=(0, 4))
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
        self._indicator.configure(text_color=CLR_RECORDING if self._pulse_on else "#7f3d4a")
        self._root.after(500, self._pulse)

    def _toggle_history(self):
        self._hist_visible = not self._hist_visible
        if self._hist_visible:
            self._history_panel.pack(fill="both", expand=True)
            self._root.geometry(f"{WINDOW_W}x{HISTORY_H + self._banner_h}")
            self._root.resizable(False, True)
            self._hist_btn.configure(text="▲ History")
        else:
            self._history_panel.pack_forget()
            self._root.geometry(f"{WINDOW_W}x{COMPACT_H + self._banner_h}")
            self._root.resizable(False, False)
            self._hist_btn.configure(text="▼ History")

    def _build_update_banner(self):
        self._update_banner = ctk.CTkFrame(
            self._root, fg_color="#1a2f3e", corner_radius=0, height=BANNER_H,
        )
        self._update_banner.pack_propagate(False)
        # Content populated on first show — not built here

    def _do_show_update_banner(self, latest: str, url: str):
        if not getattr(self, "_banner_built", False):
            row = ctk.CTkFrame(self._update_banner, fg_color="transparent")
            row.pack(fill="both", expand=True, padx=10)

            ctk.CTkLabel(
                row, text=f"Update available — v{latest}   ",
                text_color=CLR_AI_LABEL,
                font=ctk.CTkFont(size=10),
            ).pack(side="left")

            dl = ctk.CTkLabel(
                row, text="Download →",
                text_color="#89b4fa",
                font=ctk.CTkFont(size=10),
                cursor="hand2",
            )
            dl.pack(side="left")
            if url:
                dl.bind("<Button-1>", lambda _: webbrowser.open(url))

            ctk.CTkButton(
                row, text="✕",
                width=22, height=22,
                fg_color="transparent", hover_color=CLR_SURFACE1,
                text_color=CLR_SUBTEXT, font=ctk.CTkFont(size=9),
                corner_radius=3,
                command=self._dismiss_update_banner,
            ).pack(side="right")

            self._banner_built = True

        self._update_banner.pack(fill="x")
        self._banner_h = BANNER_H
        h = (HISTORY_H if self._hist_visible else COMPACT_H) + BANNER_H
        self._root.geometry(f"{WINDOW_W}x{h}")

    def _dismiss_update_banner(self):
        self._update_banner.pack_forget()
        self._banner_h = 0
        h = HISTORY_H if self._hist_visible else COMPACT_H
        self._root.geometry(f"{WINDOW_W}x{h}")

    def _do_set_clipboard_only(self, active: bool):
        if active:
            self._clip_badge.pack(side="left", padx=(6, 0))
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
        win.title("Settings — Clembot-dictate")
        win.geometry("340x560")
        win.configure(fg_color=CLR_BG)
        win.resizable(False, False)
        win.grab_set()   # modal
        self._settings_win = win

        # ── Hotkey section ───────────────────────────────────────────
        ctk.CTkLabel(
            win, text="⌨  Hotkey",
            text_color=CLR_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
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
            border_color=CLR_SURFACE2,
            text_color=CLR_AI_LABEL,
            font=ctk.CTkFont(size=13, weight="bold"),
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
                    status_label.configure(text="✓ Applied", text_color="#a6e3a1")
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
            win, text="🚀  Startup",
            text_color=CLR_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
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
            button_hover_color="#6bcfde",
            progress_color="#1e3a4a",
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
                        text="✓ Registered" if ok else "✗ Failed",
                        text_color="#a6e3a1" if ok else CLR_RECORDING,
                    )
                else:
                    ok = startup.unregister()
                    startup_status.configure(
                        text="✓ Removed" if ok else "✗ Failed",
                        text_color=CLR_SUBTEXT if ok else CLR_RECORDING,
                    )
            except Exception:
                startup_status.configure(text="✗ Error", text_color=CLR_RECORDING)

        startup_switch.configure(command=_toggle_startup)

        # ── API Key ──────────────────────────────────────────────────
        ctk.CTkFrame(win, fg_color=CLR_SURFACE2, height=1, corner_radius=0).pack(
            fill="x", padx=20, pady=(16, 0)
        )
        ctk.CTkLabel(
            win, text="🔑  AI Key",
            text_color=CLR_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=20, pady=(16, 2))

        ctk.CTkLabel(
            win, text="Anthropic API key — stored in Windows Credential Manager.",
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
                api_key_status.configure(text="✓ Saved", text_color="#a6e3a1")
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
            win, text="ℹ  About",
            text_color=CLR_TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=20, pady=(16, 6))

        # Inline hyperlink requires tk.Text with a tagged region
        about = tk.Text(
            win, wrap="word", width=1, height=5,
            bg=CLR_BG, fg=CLR_SUBTEXT,
            font=("Segoe UI", 10),
            relief="flat", borderwidth=0, highlightthickness=0,
            padx=0, pady=0, cursor="arrow", spacing3=3,
        )
        about.pack(fill="x", padx=20, pady=(0, 16))

        about.insert("end", f"Clembot-dictate v{VERSION}  ·  built by the ")
        about.insert("end", "Wanessa Labs", "link")
        about.insert("end", " team.")
        about.insert("end", "\n\nNote: Windows only — Mac already has great open source tooling for this.", "note")
        about.tag_configure("note", foreground=CLR_SUBTEXT, font=("Segoe UI", 9))

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
            hrow, text="Copy",
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
                text="↺ Re-run" if has_refined else "✦ Run AI",
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
                raw_block, text="RAW",
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
            ai_frame, text="✦ AI",
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
            refs.run_btn.configure(state="normal", text="↺ Re-run")

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
                    refs.ai_expand_btn.configure(text="▼ more")
                    refs._ai_expanded[0] = False
                else:
                    refs.ai_text.configure(height=refs._ai_full_lines[0])
                    refs.ai_expand_btn.configure(text="▲ less")
                    refs._ai_expanded[0] = True
            refs.ai_expand_btn = ctk.CTkButton(
                refs.ai_frame, text="▼ more",
                height=18, fg_color="transparent",
                hover_color=CLR_SURFACE2, text_color=CLR_SUBTEXT,
                font=ctk.CTkFont(size=9), anchor="w",
                command=_toggle,
            )
            refs.ai_expand_btn.pack(fill="x", padx=8, pady=(0, 5))
        else:
            refs._ai_expanded[0] = False
            refs.ai_expand_btn.configure(text="▼ more")
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
            font=("Segoe UI", size), bg=bg, fg=fg,
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
                btn_holder[0].configure(text="▼ more")
                expanded[0] = False
            else:
                widget.configure(height=full_lines[0])
                btn_holder[0].configure(text="▲ less")
                expanded[0] = True

        def _check():
            try:
                lines = widget.count("1.0", "end", "displaylines")[0]
                full_lines[0] = lines
                widget.configure(height=min(MAX_LINES, lines))
                if lines > MAX_LINES and btn_holder[0] is None:
                    btn = ctk.CTkButton(
                        parent, text="▼ more",
                        height=18, fg_color="transparent",
                        hover_color=CLR_SURFACE2, text_color=CLR_SUBTEXT,
                        font=ctk.CTkFont(size=9), anchor="w",
                        command=_toggle,
                    )
                    btn.pack(fill="x", padx=8, pady=(0, 4))
                    btn_holder[0] = btn
            except Exception:
                pass

        parent.after(120, _check)
        return widget
