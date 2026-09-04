"""The conversation list."""

from __future__ import annotations

import time
import tkinter as tk

from ..models import Chat
from ..people import BADGE_NAMES
from ..textutil import elide
from ..theme import Theme
from .scrollframe import ScrollFrame, bind_mousewheel


class ChatRow(tk.Frame):
    """One conversation: avatar, name, a preview of the last message, unread count."""

    def __init__(self, master: tk.Misc, app, chat: Chat, sidebar: "Sidebar") -> None:
        self.app, self.chat, self.sidebar = app, chat, sidebar
        self.theme: Theme = app.theme
        super().__init__(master, takefocus=True, highlightthickness=2, cursor="hand2")
        self.selected = False
        self._hover = False

        self.stripe = tk.Frame(self, width=7)
        self.stripe.pack(side="left", fill="y")

        avatar = app.images.avatar(chat.key, 44)
        self.avatar = tk.Label(self, image=avatar, borderwidth=0)
        self.avatar.image = avatar
        self.avatar.pack(side="left", padx=(8, 10), pady=8)

        self.right = tk.Frame(self)
        self.right.pack(side="right", padx=(6, 10), pady=8)
        self.stamp = tk.Label(self.right, anchor="e")
        self.stamp.pack()
        self.badge = tk.Label(self.right, padx=7, pady=1)
        self.badge.pack(pady=(4, 0))

        self.middle = tk.Frame(self)
        self.middle.pack(side="left", fill="both", expand=True, pady=8)
        self.name = tk.Label(self.middle, text=chat.person.name, anchor="w")
        self.name.pack(fill="x")
        self.preview = tk.Label(self.middle, anchor="w", justify="left")
        self.preview.pack(fill="x")

        for widget in (self, self.avatar, self.middle, self.name, self.preview,
                       self.right, self.stamp, self.badge, self.stripe):
            widget.bind("<Button-1>", self._activate, add="+")
            widget.bind("<Enter>", self._enter, add="+")
            widget.bind("<Leave>", self._leave, add="+")
        self.bind("<Return>", self._activate, add="+")
        self.bind("<space>", self._activate, add="+")
        self.bind("<FocusIn>", lambda _e: self.refresh(), add="+")
        self.bind("<FocusOut>", lambda _e: self.refresh(), add="+")
        self.refresh()

    def _activate(self, _event=None) -> str:
        self.focus_set()
        self.app.open_chat(self.chat.key)
        return "break"

    def _enter(self, _event=None) -> None:
        self._hover = True
        self.refresh()

    def _leave(self, _event=None) -> None:
        self._hover = False
        self.refresh()

    def refresh(self) -> None:
        theme, palette = self.theme, self.theme.p
        color = self.chat.person.color
        if self.selected:
            background = theme.row_selected(color)
        elif self._hover:
            background = palette.panel_alt
        else:
            background = palette.panel
        ring = palette.focus if self.focus_get() is self else background

        last = self.chat.last()
        preview = last.preview() if last else "No messages yet"
        if last is not None and last.mine:
            preview = f"You: {preview}"
        preview = " ".join(preview.split())

        # Work out how much room the middle column really has, so long names
        # and previews are shortened instead of sliding under the time stamp.
        # The list has a known width, so use that rather than the live
        # geometry -- rows are painted before Tk has laid them out.
        row_width = self.sidebar.preferred_width() - 30
        stamp_width = theme.font("tiny").measure("00:00") + 22
        text_width = max(60, row_width - 7 - 44 - 18 - stamp_width - 10)
        # Show the badge word when it fits; the name itself matters more.
        name = f"{self.chat.person.name}  ({BADGE_NAMES[self.chat.person.badge]})"
        if theme.font("name").measure(name) > text_width:
            name = elide(self.chat.person.name, theme.font("name"), text_width)
        preview = elide(preview, theme.font("small"), text_width)

        self.configure(background=background, highlightbackground=ring, highlightcolor=ring)
        highlighted = self.selected or self.chat.unread
        self.stripe.configure(background=color if highlighted else background)
        for widget in (self.avatar, self.middle, self.right):
            widget.configure(background=background)
        self.name.configure(
            text=name, background=background,
            foreground=theme.contact_ink(color), font=theme.font("name"),
        )
        self.preview.configure(
            text=preview, background=background,
            foreground=palette.text if self.chat.unread else palette.text_soft,
            font=theme.font("small"),
        )
        self.stamp.configure(
            text=short_time(last.ts) if last else "", background=background,
            foreground=palette.text_soft, font=theme.font("tiny"),
        )
        if self.chat.unread:
            self.badge.configure(
                text=str(self.chat.unread), background=color,
                foreground="#ffffff" if palette.key != "contrast" else palette.accent_text,
                font=theme.font("tiny"),
            )
            if palette.key == "contrast":
                self.badge.configure(background=palette.accent)
            self.badge.pack(pady=(4, 0))
        else:
            self.badge.pack_forget()
            self.badge.configure(background=background)

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self.refresh()


class Sidebar(tk.Frame):
    def __init__(self, master: tk.Misc, app) -> None:
        self.app = app
        self.theme: Theme = app.theme
        super().__init__(master, background=self.theme.p.panel, width=self.preferred_width())
        self.pack_propagate(False)

        self.heading = tk.Label(self, text="Chats", anchor="w")
        self.heading.pack(fill="x", padx=14, pady=(12, 2))

        self.search_row = tk.Frame(self, highlightthickness=2)
        self.search_row.pack(fill="x", padx=12, pady=(4, 8))
        icon = app.images.icon("search", "dark", 20)
        self.search_icon = tk.Label(self.search_row, image=icon, borderwidth=0)
        self.search_icon.image = icon
        self.search_icon.pack(side="left", padx=(8, 4), pady=4)
        self.search_var = tk.StringVar()
        self.search = tk.Entry(self.search_row, textvariable=self.search_var,
                               borderwidth=0, highlightthickness=0)
        self.search.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=4)
        self.search_var.trace_add("write", lambda *_: self.rebuild())

        self.hint = tk.Label(self, anchor="w", justify="left",
                             text="Search names or words in messages")
        self.hint.pack(fill="x", padx=14)

        self.scroller = ScrollFrame(self, background=self.theme.p.panel)
        self.scroller.pack(fill="both", expand=True, pady=(6, 0))

        self.rows: dict[str, ChatRow] = {}
        self.rebuild()

    def preferred_width(self) -> int:
        """Wider list for bigger text, so names still have room to breathe."""
        return min(580, max(380, round(260 * self.theme.scale + 120)))

    def rebuild(self) -> None:
        body = self.scroller.body
        for child in body.winfo_children():
            child.destroy()
        self.rows.clear()
        chats = self.app.store.matching(self.search_var.get())
        if not chats:
            tk.Label(body, text="Nothing found", background=self.theme.p.panel,
                     foreground=self.theme.p.text_soft, font=self.theme.font("body")).pack(pady=20)
        for chat in chats:
            row = ChatRow(body, self.app, chat, self)
            row.pack(fill="x", padx=6, pady=2)
            row.set_selected(chat.key == self.app.current_key)
            bind_mousewheel(row, self.scroller.canvas)
            for child in row.winfo_children():
                bind_mousewheel(child, self.scroller.canvas)
            self.rows[chat.key] = row
        self.refresh()

    def refresh(self) -> None:
        theme, palette = self.theme, self.theme.p
        self.configure(background=palette.panel, width=self.preferred_width())
        self.heading.configure(
            background=palette.panel, foreground=palette.text, font=theme.font("title"),
            text=f"Chats  ({self.app.store.total_unread()} unread)"
            if self.app.store.total_unread() else "Chats",
        )
        self.search_row.configure(background=palette.panel_alt,
                                  highlightbackground=palette.line, highlightcolor=palette.focus)
        self.search_icon.configure(background=palette.panel_alt)
        icon = self.app.images.icon("search", theme.icon_ink(palette.panel_alt), 20)
        self.search_icon.configure(image=icon)
        self.search_icon.image = icon
        self.search.configure(background=palette.panel_alt, foreground=palette.text,
                              insertbackground=palette.text, font=theme.font("body"))
        self.hint.configure(background=palette.panel, foreground=palette.text_soft,
                            font=theme.font("tiny"))
        self.scroller.set_background(palette.panel)
        for key, row in self.rows.items():
            row.set_selected(key == self.app.current_key)

    def select(self, key: str) -> None:
        for row_key, row in self.rows.items():
            row.set_selected(row_key == key)


def short_time(ts: float) -> str:
    now = time.time()
    if now - ts < 86400 and time.localtime(ts).tm_mday == time.localtime(now).tm_mday:
        return time.strftime("%H:%M", time.localtime(ts))
    if now - ts < 6 * 86400:
        return time.strftime("%a", time.localtime(ts))
    return time.strftime("%d/%m", time.localtime(ts))
