"""The picture board: send a message by choosing a picture.

This is the part of the app aimed squarely at people who find typing hard --
symbol-based (AAC style) communication.  Every tile is a large picture with its
word underneath, grouped into categories, and choosing one sends a complete,
polite sentence.
"""

from __future__ import annotations

import tkinter as tk

from ..pictograms import CATEGORIES, Pictogram, in_category
from ..theme import Theme, mix
from .buttons import Tooltip
from .scrollframe import ScrollFrame, bind_mousewheel


class PictureTile(tk.Frame):
    """One picture plus its word, clickable and focusable."""

    def __init__(self, master: tk.Misc, theme: Theme, pictogram: Pictogram,
                 image, command) -> None:
        super().__init__(master, takefocus=True, highlightthickness=3, cursor="hand2")
        self.theme, self.pictogram, self.command = theme, pictogram, command
        self._hover = False

        self.picture = tk.Label(self, image=image, borderwidth=0)
        self.picture.image = image
        self.picture.pack(padx=8, pady=(8, 4))
        self.caption = tk.Label(self, text=pictogram.label, borderwidth=0)
        self.caption.pack(padx=8, pady=(0, 8))

        for widget in (self, self.picture, self.caption):
            widget.bind("<Button-1>", self._activate, add="+")
            widget.bind("<Enter>", self._enter, add="+")
            widget.bind("<Leave>", self._leave, add="+")
        self.bind("<Return>", self._activate, add="+")
        self.bind("<space>", self._activate, add="+")
        self.bind("<FocusIn>", lambda _e: self.refresh(), add="+")
        self.bind("<FocusOut>", lambda _e: self.refresh(), add="+")
        Tooltip(self, f"Send: “{pictogram.message}”", theme)
        self.refresh()

    def refresh(self) -> None:
        palette = self.theme.p
        if palette.key == "contrast":
            background = "#1c1c1c" if self._hover else "#000000"
            border = palette.line
        else:
            blend = 0.82 if not self._hover else 0.7
            background = mix(self.pictogram.color, palette.panel, blend)
            border = self.pictogram.color
        focused = self.focus_get() is self
        ring = palette.focus if focused else border
        self.configure(background=background, highlightbackground=ring, highlightcolor=ring)
        self.picture.configure(background=background)
        self.caption.configure(
            background=background,
            foreground=palette.text,
            font=self.theme.font("body_bold"),
        )

    def _enter(self, _event=None) -> None:
        self._hover = True
        self.refresh()

    def _leave(self, _event=None) -> None:
        self._hover = False
        self.refresh()

    def _activate(self, _event=None) -> str:
        self.focus_set()
        self.command(self.pictogram)
        return "break"


class PictureBoard(tk.Frame):
    def __init__(self, master: tk.Misc, app) -> None:
        self.app = app
        self.theme: Theme = app.theme
        super().__init__(master, background=self.theme.p.panel, highlightthickness=0)

        self.category = CATEGORIES[0]
        self.header = tk.Frame(self, background=self.theme.p.panel)
        self.header.pack(fill="x", padx=10, pady=(8, 4))
        self.title = tk.Label(self.header, text="Picture board — tap a picture to send it")
        self.title.pack(side="left")

        self.tabs = tk.Frame(self, background=self.theme.p.panel)
        self.tabs.pack(fill="x", padx=10)
        self.tab_buttons: dict[str, tk.Label] = {}

        self.scroller = ScrollFrame(self, background=self.theme.p.panel)
        self.scroller.pack(fill="both", expand=True, padx=6, pady=6)

        self._build_tabs()
        self.refresh()

    def _build_tabs(self) -> None:
        for child in self.tabs.winfo_children():
            child.destroy()
        self.tab_buttons.clear()
        for name in CATEGORIES:
            tab = tk.Label(self.tabs, text=name, padx=12, pady=6, cursor="hand2",
                           takefocus=True, highlightthickness=2, borderwidth=0)
            tab.pack(side="left", padx=(0, 6))
            tab.bind("<Button-1>", lambda _e, n=name: self.select_category(n))
            tab.bind("<Return>", lambda _e, n=name: self.select_category(n))
            tab.bind("<space>", lambda _e, n=name: self.select_category(n))
            tab.bind("<FocusIn>", lambda _e: self.refresh())
            tab.bind("<FocusOut>", lambda _e: self.refresh())
            self.tab_buttons[name] = tab

    def select_category(self, name: str) -> None:
        self.category = name
        self.refresh()
        self.scroller.scroll_to_top()

    def refresh(self) -> None:
        palette = self.theme.p
        self.configure(background=palette.panel)
        self.header.configure(background=palette.panel)
        self.tabs.configure(background=palette.panel)
        self.title.configure(
            background=palette.panel, foreground=palette.text_soft,
            font=self.theme.font("body_bold"),
        )
        self.scroller.set_background(palette.panel)

        for name, tab in self.tab_buttons.items():
            active = name == self.category
            background = palette.accent if active else palette.panel_alt
            foreground = palette.accent_text if active else palette.text
            ring = palette.focus if tab.focus_get() is tab else background
            tab.configure(
                background=background, foreground=foreground, font=self.theme.font("body_bold"),
                highlightbackground=ring, highlightcolor=ring,
            )

        self._fill_grid()

    def _fill_grid(self) -> None:
        body = self.scroller.body
        for child in body.winfo_children():
            child.destroy()
        size = 128 if self.theme.scale >= 1.15 else 64
        columns = 4
        for index, pictogram in enumerate(in_category(self.category)):
            image = self.app.images.pictogram(pictogram.key, size)
            tile = PictureTile(body, self.theme, pictogram, image, self.app.send_pictogram)
            tile.grid(row=index // columns, column=index % columns,
                      padx=6, pady=6, sticky="nsew")
            bind_mousewheel(tile, self.scroller.canvas)
            bind_mousewheel(tile.picture, self.scroller.canvas)
            bind_mousewheel(tile.caption, self.scroller.canvas)
        for column in range(columns):
            body.grid_columnconfigure(column, weight=1)
