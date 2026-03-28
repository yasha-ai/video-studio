"""Collapsible log panel with GUI logging handler for CustomTkinter."""

import logging
import tkinter as tk
from datetime import datetime

import customtkinter as ctk

try:
    from .theme import C, L
except ImportError:
    from ui.theme import C, L

LEVEL_COLORS = {
    "ERROR": C["red"],
    "WARNING": C["orange"],
    "INFO": C["text"],
    "DEBUG": C["text3"],
}

MAX_LINES = 1000


class LogPanel(ctk.CTkFrame):
    """Collapsible log panel that docks to the bottom of the main window."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=C["surface"], corner_radius=0, **kwargs)

        self._expanded = False

        # --- Header bar (always visible) ---
        self._header = ctk.CTkFrame(self, fg_color=C["surface2"], height=32, corner_radius=0)
        self._header.pack(fill="x", side="top")
        self._header.pack_propagate(False)

        self._toggle_btn = ctk.CTkButton(
            self._header,
            text="\u25b6 Logs",
            width=80,
            height=24,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=C["surface3"],
            text_color=C["text2"],
            anchor="w",
            command=self.toggle,
        )
        self._toggle_btn.pack(side="left", padx=6, pady=4)

        self._clear_btn = ctk.CTkButton(
            self._header,
            text="Clear",
            width=50,
            height=24,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=C["surface3"],
            text_color=C["text3"],
            command=self.clear,
        )
        self._clear_btn.pack(side="right", padx=6, pady=4)

        # --- Log body (shown when expanded) ---
        self._body = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)

        self._textbox = ctk.CTkTextbox(
            self._body,
            fg_color=C["bg"],
            text_color=C["text"],
            font=ctk.CTkFont(family="Courier", size=12),
            wrap="word",
            state="disabled",
            corner_radius=0,
            border_width=0,
            height=200,
        )
        self._textbox.pack(fill="both", expand=True, padx=0, pady=0)

        # Configure color tags on the underlying tk.Text widget
        inner_text: tk.Text = self._textbox._textbox  # noqa: access internal widget
        for level, color in LEVEL_COLORS.items():
            inner_text.tag_configure(level, foreground=color)

        # Make text selectable + copyable (block typing but allow selection)
        inner_text.configure(state="normal")
        inner_text.bind("<Key>", lambda e: "break" if e.keysym not in ("c", "C", "a", "A") or not (e.state & 0x8 or e.state & 0x4) else None)

        # Context menu
        def _show_log_menu(event):
            menu = tk.Menu(inner_text, tearoff=0, bg="#2d333b", fg="#e6edf3",
                           activebackground="#2ea043", activeforeground="#e6edf3",
                           font=("Helvetica", 12))
            menu.add_command(label="Copy", command=lambda: self._copy_selection())
            menu.add_command(label="Copy All", command=lambda: self._copy_all())
            menu.add_separator()
            menu.add_command(label="Clear", command=self.clear)
            menu.tk_popup(event.x_root, event.y_root)

        inner_text.bind("<Button-3>", _show_log_menu)
        inner_text.bind("<Control-Button-1>", _show_log_menu)

        # Cmd+C / Ctrl+C for copy
        for mod in ("Command", "Control"):
            inner_text.bind(f"<{mod}-c>", lambda e: self._copy_selection())
            inner_text.bind(f"<{mod}-C>", lambda e: self._copy_selection())
            inner_text.bind(f"<{mod}-a>", lambda e: (inner_text.tag_add("sel", "1.0", "end"), "break")[-1])
            inner_text.bind(f"<{mod}-A>", lambda e: (inner_text.tag_add("sel", "1.0", "end"), "break")[-1])

        self._inner_text = inner_text
        self._line_count = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def toggle(self):
        """Expand or collapse the log body."""
        if self._expanded:
            self._body.pack_forget()
            self._toggle_btn.configure(text="\u25b6 Logs")
        else:
            self._body.pack(fill="both", expand=True, side="top")
            self._toggle_btn.configure(text="\u25bc Logs")
        self._expanded = not self._expanded

    def _copy_selection(self):
        """Copy selected text to clipboard."""
        try:
            text = self._inner_text.selection_get()
            self._inner_text.clipboard_clear()
            self._inner_text.clipboard_append(text)
        except tk.TclError:
            pass

    def _copy_all(self):
        """Copy all log text to clipboard."""
        text = self._inner_text.get("1.0", "end").strip()
        if text:
            self._inner_text.clipboard_clear()
            self._inner_text.clipboard_append(text)

    def clear(self):
        """Remove all log entries."""
        self._inner_text.delete("1.0", "end")
        self._line_count = 0

    def append(self, message: str, level: str = "INFO"):
        """Append a log line (thread-safe)."""
        self._textbox.after(0, self._append_on_main, message, level)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _append_on_main(self, message: str, level: str):
        tag = level if level in LEVEL_COLORS else "INFO"
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {level:<7} {message}\n"

        self._inner_text.insert("end", line, tag)
        self._line_count += 1

        # Auto-trim old entries
        if self._line_count > MAX_LINES:
            trim = self._line_count - MAX_LINES
            self._inner_text.delete("1.0", f"{trim + 1}.0")
            self._line_count = MAX_LINES

        self._inner_text.see("end")


class GUILogHandler(logging.Handler):
    """A logging.Handler that routes records to a LogPanel (thread-safe)."""

    def __init__(self, log_panel: LogPanel, level=logging.DEBUG):
        super().__init__(level)
        self._panel = log_panel

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self._panel.append(msg, record.levelname)
        except Exception:
            self.handleError(record)
