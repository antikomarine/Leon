"""Where messages are written: a big text box and large, obvious buttons."""

from __future__ import annotations

import tkinter as tk

from ..theme import Theme
from .buttons import ColorButton

PLACEHOLDER = "Write a message…"


class Composer(tk.Frame):
    def __init__(self, master: tk.Misc, app) -> None:
        self.app = app
        self.theme: Theme = app.theme
        super().__init__(master, background=self.theme.p.panel)

        self.board_button = ColorButton(
            self, self.theme, "Pictures", command=app.toggle_board, style="solid",
            image=app.images.icon("board", "light", self.theme.icon_size()),
            tooltip="Open the picture board (Ctrl+B)",
        )
        self.board_button.pack(side="left", padx=(10, 6), pady=10)

        self.send_button = ColorButton(
            self, self.theme, "Send", command=self.send, style="solid",
            image=app.images.icon("send", "light", self.theme.icon_size()),
            tooltip="Send this message (Enter)",
        )
        self.send_button.pack(side="right", padx=10, pady=10)

        self.box = tk.Frame(self, highlightthickness=3)
        self.box.pack(side="left", fill="both", expand=True, pady=10)
        # width=1: the box grows to fill whatever room is left, it never
        # demands room of its own and pushes the Send button off screen.
        self.entry = tk.Text(self.box, height=2, width=1, wrap="word", borderwidth=0,
                             highlightthickness=0, padx=10, pady=8)
        self.entry.pack(fill="both", expand=True)
        self._placeholder_showing = False

        self.entry.bind("<Return>", self._on_return)
        self.entry.bind("<Shift-Return>", lambda _e: None)
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<KeyRelease>", lambda _e: self.app.on_typing())
        self._show_placeholder()
        self.refresh()

    # -- text handling -----------------------------------------------------
    def _show_placeholder(self) -> None:
        if not self.text().strip():
            self.entry.delete("1.0", "end")
            self.entry.insert("1.0", PLACEHOLDER)
            self._placeholder_showing = True
            self.refresh()

    def _on_focus_in(self, _event=None) -> None:
        if self._placeholder_showing:
            self.entry.delete("1.0", "end")
            self._placeholder_showing = False
        self.refresh()

    def _on_focus_out(self, _event=None) -> None:
        self._show_placeholder()
        self.refresh()

    def text(self) -> str:
        if self._placeholder_showing:
            return ""
        return self.entry.get("1.0", "end").strip()

    def clear(self) -> None:
        self.entry.delete("1.0", "end")
        self._placeholder_showing = False

    def focus_entry(self) -> None:
        self.entry.focus_set()

    def insert(self, text: str) -> None:
        self._on_focus_in()
        self.entry.insert("end", text)
        self.focus_entry()

    def _on_return(self, _event=None) -> str:
        self.send()
        return "break"

    def send(self) -> None:
        message = self.text()
        if not message:
            self.app.announce("Write something first, or choose a picture.")
            self.focus_entry()
            return
        self.clear()
        self.app.send_text(message)

    # -- appearance --------------------------------------------------------
    def refresh(self) -> None:
        theme, palette = self.theme, self.theme.p
        color = self.app.current_color()
        self.configure(background=palette.panel)
        self.box.configure(background=palette.panel_alt, highlightbackground=color,
                           highlightcolor=palette.focus)
        self.entry.configure(
            background=palette.panel_alt,
            foreground=palette.text_soft if self._placeholder_showing else palette.text,
            insertbackground=palette.text,
            font=theme.font("body"),
            selectbackground=color,
            selectforeground="#ffffff",
        )
        # Icons follow the button colour, so a pale button gets dark artwork.
        size = theme.icon_size()
        accent = palette.accent
        self.board_button.set_image(
            self.app.images.icon("board", theme.icon_ink(accent), size))
        self.send_button.set_image(self.app.images.icon("send", theme.icon_ink(color), size))
        self.send_button.color = color
        self.board_button.color = None
        self.send_button.refresh()
        self.board_button.refresh()
