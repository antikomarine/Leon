"""The main window: app bar, conversation list, chat panel, picture board."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from . import people
from .assets import Images
from .models import DELIVERED, Message, READ, SENT, Store
from .pictograms import Pictogram
from .speech import Speaker
from .textutil import elide
from .theme import Theme
from .widgets.buttons import ColorButton
from .widgets.chatview import ChatView
from .widgets.composer import Composer
from .widgets.flowbar import FlowBar
from .widgets.pictureboard import PictureBoard
from .widgets.sidebar import Sidebar
from . import APP_NAME, __version__
from . import bots

HELP_TEXT = f"""{APP_NAME} {__version__} — a colourful, picture-first messenger

Getting around
  • Pick a conversation on the left; every contact has their own colour
    and their own badge shape, so you never have to rely on colour alone.
  • Type in the box at the bottom and press Enter to send.
  • Press the “Pictures” button to send a picture message instead of typing.

Made to be easy to read
  • Bigger text / Smaller text change every word in the app at once.
  • Colours switches between Bright, Night and High contrast.
  • Read aloud speaks new messages, and any message you click on.
  • Every button shows a picture and a word, never a picture on its own.
  • Everything can be reached with the keyboard: Tab moves, Enter or Space
    presses, and the focused item is outlined in a bright colour.

Keyboard shortcuts
  Enter              Send the message
  Shift + Enter      Start a new line
  Ctrl + B           Open or close the picture board
  Ctrl + K           Jump to search
  Ctrl + Plus/Minus  Bigger or smaller text
  Ctrl + T           Next colour scheme
  Ctrl + R           Read the last message aloud
  Ctrl + Up / Down   Previous or next conversation
  F1                 This help
  Escape             Close the picture board

The contacts here are simulated: they reply on this computer, nothing is
sent over the internet and no account is needed. Conversations are stored
in a small JSON file in your home folder (~/.marasender/chats.json).
"""


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.theme = Theme()
        self.images = Images()
        self.store = Store()
        self.speaker = Speaker()
        self.read_aloud = False
        self.current_key = self.store.ordered()[0].key
        self.board_open = False
        self._timers: list[str] = []

        root.title(f"{APP_NAME} — messages in colour")
        root.geometry("1220x780")
        root.minsize(880, 560)
        root.configure(background=self.theme.p.window)

        self._build()
        self.theme.on_change(self.refresh)
        self._bind_keys()
        root.bind("<Destroy>", self._on_destroy, add="+")
        self.open_chat(self.current_key)
        self.refresh()
        self.announce("Welcome! Press F1 at any time for help.")
        root.protocol("WM_DELETE_WINDOW", self.quit)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build(self) -> None:
        root = self.root
        self.bar = tk.Frame(root, background=self.theme.p.bar)
        self.bar.pack(fill="x", side="top")

        self.bar_top = tk.Frame(self.bar, background=self.theme.p.bar)
        self.bar_top.pack(fill="x")
        self.bar_title = tk.Label(self.bar_top, text=APP_NAME)
        self.bar_title.pack(side="left", padx=(16, 8), pady=(8, 2))
        self.bar_subtitle = tk.Label(self.bar_top, text="messages in colour, with pictures")
        self.bar_subtitle.pack(side="left", pady=(8, 2))

        # The accessibility controls live on their own line and wrap when the
        # text size makes them too wide for one.
        self.toolbar = FlowBar(self.bar, align="right", background=self.theme.p.bar)
        self.toolbar.pack(fill="x")

        icon_size = self.theme.icon_size()
        self.bar_buttons: list[ColorButton] = []

        def bar_button(text: str, icon: str, command, tooltip: str) -> ColorButton:
            button = ColorButton(
                self.toolbar, self.theme, text, command=command, style="quiet",
                image=self.images.icon(icon, "light", icon_size), tooltip=tooltip, compact=True,
            )
            self.toolbar.add(button)
            button._icon_name = icon
            self.bar_buttons.append(button)
            return button

        self.bigger_button = bar_button(
            "Bigger text", "text_bigger", lambda: self.change_text_size(1),
            "Make every word in the app bigger (Ctrl+Plus)",
        )
        self.smaller_button = bar_button(
            "Smaller text", "text_smaller", lambda: self.change_text_size(-1),
            "Make every word in the app smaller (Ctrl+Minus)",
        )
        self.theme_button = bar_button(
            "Colours: Bright", "contrast", self.cycle_palette, "Change the colour scheme (Ctrl+T)"
        )
        self.speak_button = bar_button(
            "Read aloud: off", "speak", self.toggle_read_aloud,
            "Speak new messages out loud (Ctrl+R reads the last one)",
        )
        self.help_button = bar_button("Help", "info", self.show_help, "Help and shortcuts (F1)")

        self.body = tk.Frame(root, background=self.theme.p.window)
        self.body.pack(fill="both", expand=True)

        self.sidebar = Sidebar(self.body, self)
        self.sidebar.pack(side="left", fill="y")
        self.divider = tk.Frame(self.body, width=2, background=self.theme.p.line)
        self.divider.pack(side="left", fill="y")

        self.panel = tk.Frame(self.body, background=self.theme.p.canvas)
        self.panel.pack(side="left", fill="both", expand=True)

        # -- chat header --
        self.header = tk.Frame(self.panel, background=self.theme.p.panel)
        self.header.pack(fill="x")
        self.header_avatar = tk.Label(self.header, borderwidth=0)
        self.header_avatar.pack(side="left", padx=(14, 10), pady=10)
        self.call_button = ColorButton(
            self.header, self.theme, "Call", command=lambda: self.not_yet("Voice calls"),
            style="ghost", image=self.images.icon("call", "dark", icon_size),
            tooltip="Voice call (demo only)",
        )
        self.call_button.pack(side="right", padx=(4, 14), pady=10)
        self.video_button = ColorButton(
            self.header, self.theme, "Video", command=lambda: self.not_yet("Video calls"),
            style="ghost", image=self.images.icon("video", "dark", icon_size),
            tooltip="Video call (demo only)",
        )
        self.video_button.pack(side="right", padx=4, pady=10)

        self.header_text = tk.Frame(self.header, background=self.theme.p.panel)
        self.header_text.pack(side="left", fill="both", expand=True, pady=10)
        self.header_name = tk.Label(self.header_text, anchor="w")
        self.header_name.pack(fill="x")
        self.header_status = tk.Label(self.header_text, anchor="w")
        self.header_status.pack(fill="x")
        self._header_width = 0
        self.header_text.bind("<Configure>", self._on_header_resize)
        self.header_line = tk.Frame(self.panel, height=2, background=self.theme.p.line)
        self.header_line.pack(fill="x")

        # -- composer, board, messages --
        # Packing order is deliberate: Tk hands out space in the order widgets
        # were packed, so the composer is claimed first and can never be
        # squeezed off the bottom of the window by a tall picture board.
        self.composer = Composer(self.panel, self)
        self.composer.pack(side="bottom", fill="x")
        self.composer_line = tk.Frame(self.panel, height=2, background=self.theme.p.line)
        self.composer_line.pack(side="bottom", fill="x")

        self.chatview = ChatView(self.panel, self)
        self.chatview.pack(side="top", fill="both", expand=True)

        self.board = PictureBoard(self.panel, self)   # packed only when open
        self.panel.bind("<Configure>", self._on_panel_resize)

        self.status = tk.Label(root, anchor="w", padx=14, pady=5)
        self.status.pack(fill="x", side="bottom")

    def _bind_keys(self) -> None:
        root = self.root
        root.bind("<F1>", lambda _e: self.show_help())
        root.bind("<Control-b>", lambda _e: self.toggle_board())
        root.bind("<Control-B>", lambda _e: self.toggle_board())
        root.bind("<Control-k>", lambda _e: self.focus_search())
        root.bind("<Control-t>", lambda _e: self.cycle_palette())
        root.bind("<Control-r>", lambda _e: self.read_last_message())
        root.bind("<Control-plus>", lambda _e: self.change_text_size(1))
        root.bind("<Control-equal>", lambda _e: self.change_text_size(1))
        root.bind("<Control-KP_Add>", lambda _e: self.change_text_size(1))
        root.bind("<Control-minus>", lambda _e: self.change_text_size(-1))
        root.bind("<Control-KP_Subtract>", lambda _e: self.change_text_size(-1))
        root.bind("<Control-Up>", lambda _e: self.step_chat(-1))
        root.bind("<Control-Down>", lambda _e: self.step_chat(1))
        root.bind("<Escape>", lambda _e: self.close_board())

    # ------------------------------------------------------------------
    # Helpers used by the widgets
    # ------------------------------------------------------------------
    def later(self, milliseconds: int, callback) -> None:
        """A tracked ``after``: every timer is cancelled when the app closes."""
        self._timers.append(self.root.after(milliseconds, callback))
        if len(self._timers) > 64:
            self._timers = self._timers[-64:]

    def _on_destroy(self, event=None) -> None:
        if event is not None and event.widget is not self.root:
            return
        for timer in self._timers:
            try:
                self.root.after_cancel(timer)
            except Exception:
                pass
        self._timers.clear()

    def person_for(self, key: str) -> people.Person:
        return people.get(key)

    @property
    def current_chat(self):
        return self.store.chats.get(self.current_key)

    def current_color(self) -> str:
        """The colour of the open conversation, adjusted for the palette."""
        chat = self.current_chat
        if chat is None:
            return self.theme.p.accent
        return self.theme.contact_ink(chat.person.color)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def open_chat(self, key: str) -> None:
        self.current_key = key
        chat = self.store.chats[key]
        chat.mark_read()
        self.store.save()
        self.chatview.show(chat)
        self.sidebar.select(key)
        self.sidebar.refresh()
        for row in self.sidebar.rows.values():
            row.refresh()
        self.refresh_header()
        self.composer.refresh()
        self.announce(f"Now reading your chat with {chat.person.name}.")

    def step_chat(self, delta: int) -> None:
        keys = [chat.key for chat in self.store.ordered()]
        if self.current_key not in keys:
            return
        index = (keys.index(self.current_key) + delta) % len(keys)
        self.open_chat(keys[index])

    def send_text(self, text: str) -> None:
        self._send(Message(sender="me", text=text, status=SENT))

    def send_pictogram(self, pictogram: Pictogram) -> None:
        self._send(Message(sender="me", text=pictogram.message,
                           picture=pictogram.key, status=SENT))
        self.announce(f"Sent the picture “{pictogram.label}”.")

    def _send(self, message: Message) -> None:
        chat = self.current_chat
        if chat is None:
            return
        chat.add(message)
        self.store.save()
        self.chatview.show(chat)
        self.sidebar.rebuild()
        self.later(600, lambda: self._update_status(chat.key, message, DELIVERED))
        self.later(bots.typing_delay(message), lambda: self._start_typing(chat.key, message))

    def _update_status(self, chat_key: str, message: Message, status: str) -> None:
        if message.status != READ:
            message.status = status
            if chat_key == self.current_key:
                self.chatview.refresh()

    def _start_typing(self, chat_key: str, message: Message) -> None:
        if chat_key == self.current_key:
            self.chatview.set_typing(True)
        self.later(1100, lambda: self._deliver_reply(chat_key, message))

    def _deliver_reply(self, chat_key: str, message: Message) -> None:
        chat = self.store.chats.get(chat_key)
        if chat is None:
            return
        for earlier in chat.messages:
            if earlier.mine:
                earlier.status = READ
        reply = bots.reply_to(chat.person, message)
        chat.add(reply)
        if chat_key == self.current_key:
            chat.mark_read()
            self.chatview.set_typing(False)
            self.chatview.show(chat)
        self.store.save()
        self.sidebar.rebuild()
        if self.read_aloud:
            self.speaker.say(reply.spoken())
        name = people.get(reply.sender).name
        self.announce(f"New message from {name}: {reply.preview()}")

    def on_typing(self) -> None:
        """Called as the user types; keeps the send button in step."""
        self.composer.send_button.set_enabled(True)

    def on_message_selected(self, message: Message) -> None:
        self.announce(message.spoken())
        if self.read_aloud:
            self.speaker.say(message.spoken())

    def read_last_message(self) -> None:
        message = self.chatview.select_last()
        if message is None:
            self.announce("There are no messages in this chat yet.")
            return
        if not self.speaker.available:
            self.announce(self.speaker.unavailable_reason())
            return
        self.speaker.say(message.spoken())
        self.announce(f"Reading aloud: {message.preview()}")

    # -- picture board -----------------------------------------------------
    def toggle_board(self) -> None:
        self.close_board() if self.board_open else self.open_board()

    def open_board(self) -> None:
        if self.board_open:
            return
        self.board.configure(height=self._board_height())
        self.board.pack_propagate(False)
        self.board.pack(side="bottom", fill="x")
        self.board_open = True
        self.chatview.scroll_to_end()
        self.composer.board_button.set_text("Hide pictures")
        self.announce("Picture board open. Choose a picture to send it straight away.")

    def _board_height(self) -> int:
        """Give the board half the panel, but never at the composer's expense."""
        panel = self.panel.winfo_height() or 640
        # Whatever is left once the header, the composer and a slice of the
        # conversation have had their share.
        spare = (panel - self.header.winfo_height() - self.composer.winfo_reqheight()
                 - 120 - 8)
        return max(150, min(460, spare, int(panel * 0.5)))

    def _on_panel_resize(self, _event=None) -> None:
        if self.board_open:
            self.board.configure(height=self._board_height())

    def close_board(self) -> None:
        if not self.board_open:
            return
        self.board.pack_forget()
        self.board_open = False
        self.composer.board_button.set_text("Pictures")
        self.chatview.scroll_to_end()

    def focus_search(self) -> None:
        self.sidebar.search.focus_set()
        self.sidebar.search.select_range(0, "end")

    # -- accessibility -----------------------------------------------------
    def change_text_size(self, step: int) -> None:
        if self.theme.change_text_size(step):
            percent = round(self.theme.scale * 100)
            self.announce(f"Text size is now {percent}% of normal.")
        else:
            edge = "largest" if step > 0 else "smallest"
            self.announce(f"That is already the {edge} text size.")

    def cycle_palette(self) -> None:
        palette = self.theme.next_palette()
        self.announce(f"Colour scheme: {palette.name} — {palette.description}.")

    def toggle_read_aloud(self) -> None:
        if not self.speaker.available:
            self.announce(self.speaker.unavailable_reason())
            return
        self.read_aloud = not self.read_aloud
        state = "on" if self.read_aloud else "off"
        self.speak_button.set_text(f"Read aloud: {state}")
        self.announce(f"Read aloud is {state}.")
        if self.read_aloud:
            self.speaker.say("Read aloud is on.")

    def announce(self, text: str) -> None:
        self.status.configure(text=text)

    def not_yet(self, what: str) -> None:
        self.announce(f"{what} are not part of this demo — but messages and pictures are!")

    def show_help(self) -> None:
        window = tk.Toplevel(self.root)
        window.title(f"{APP_NAME} — help")
        window.configure(background=self.theme.p.panel)
        window.geometry("720x660")

        close = ColorButton(
            window, self.theme, "Close", command=window.destroy, style="solid",
            image=self.images.icon("close", "light", self.theme.icon_size()),
        )
        close.pack(side="bottom", pady=12)          # packed first so it is never pushed off

        holder = tk.Frame(window, background=self.theme.p.panel)
        holder.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(holder, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        text = tk.Text(holder, wrap="word", borderwidth=0, padx=18, pady=16,
                       background=self.theme.p.panel, foreground=self.theme.p.text,
                       font=self.theme.font("body"), highlightthickness=0,
                       yscrollcommand=scrollbar.set)
        text.insert("1.0", HELP_TEXT)
        text.configure(state="disabled")
        text.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=text.yview)

        window.transient(self.root)
        window.bind("<Escape>", lambda _e: window.destroy())
        close.focus_set()

    # ------------------------------------------------------------------
    # Repainting
    # ------------------------------------------------------------------
    def refresh_header(self) -> None:
        chat = self.current_chat
        theme, palette = self.theme, self.theme.p
        if chat is None:
            return
        person = chat.person
        avatar = self.images.avatar(person.key, 96 if theme.scale >= 1.3 else 44)
        self.header_avatar.configure(image=avatar, background=palette.panel)
        self.header_avatar.image = avatar
        self.header.configure(background=palette.panel)
        self.header_text.configure(background=palette.panel)
        badge = people.BADGE_NAMES[person.badge]
        # Keep the heading inside its column however large the text is.  Once
        # Tk has laid the header out its real width is the honest answer.
        room = self.header_text.winfo_width() - 12
        if room < 60:
            room = max(140, self.panel.winfo_width()
                       - self.header_avatar.winfo_reqwidth()
                       - self.call_button.winfo_reqwidth()
                       - self.video_button.winfo_reqwidth() - 110)
        self.header_name.configure(
            text=elide(person.name, theme.font("title"), room), background=palette.panel,
            foreground=theme.contact_ink(person.color), font=theme.font("title"),
        )
        self.header_status.configure(
            text=elide(f"{badge} badge · {person.about}", theme.font("small"), room),
            background=palette.panel, foreground=palette.text_soft, font=theme.font("small"),
        )
        size = theme.icon_size()
        ink = theme.icon_ink(palette.panel)
        self.call_button.set_image(self.images.icon("call", ink, size))
        self.video_button.set_image(self.images.icon("video", ink, size))
        for button in (self.call_button, self.video_button):
            button.color = theme.contact_ink(person.color)
            button.refresh()

    def _on_header_resize(self, event) -> None:
        if abs(event.width - self._header_width) > 4:
            self._header_width = event.width
            self.refresh_header()

    def refresh(self) -> None:
        theme, palette = self.theme, self.theme.p
        self.root.configure(background=palette.window)
        self.bar.configure(background=palette.bar)
        self.bar_top.configure(background=palette.bar)
        self.toolbar.configure(background=palette.bar)
        # The name is set in Bauhaus 93 where that font exists, and drawn from
        # assets/wordmark everywhere else, so it looks the same on any machine.
        if theme.has_display_font:
            self.bar_title.configure(
                image="", text=APP_NAME, background=palette.bar,
                foreground=palette.wordmark, font=theme.font("wordmark"),
            )
        else:
            wordmark = self.images.wordmark(round(28 * theme.scale))
            self.bar_title.configure(image=wordmark, text="", background=palette.bar)
            self.bar_title.image = wordmark
        self.bar_subtitle.configure(background=palette.bar, foreground=palette.bar_text,
                                    font=theme.font("small"))
        # The strapline is the first thing to go when the text gets large.
        if theme.scale >= 1.3:
            self.bar_subtitle.pack_forget()
        else:
            self.bar_subtitle.pack(side="left", pady=(8, 2), after=self.bar_title)
        size = theme.icon_size()
        for button in self.bar_buttons:
            button.set_image(self.images.icon(button._icon_name,
                                              theme.icon_ink(palette.bar), size))
            button.refresh()
        self.theme_button.set_text(f"Colours: {palette.name}")
        self.toolbar.reflow_soon()
        self.body.configure(background=palette.window)
        self.divider.configure(background=palette.line)
        self.panel.configure(background=palette.canvas)
        self.header_line.configure(background=palette.line)
        self.composer_line.configure(background=palette.line)
        self.status.configure(background=palette.panel_alt, foreground=palette.text,
                              font=theme.font("small"))
        self.sidebar.refresh()
        for row in self.sidebar.rows.values():
            row.refresh()
        self.refresh_header()
        self.board.refresh()
        self.composer.refresh()
        self.chatview.theme = theme
        self.chatview.refresh()

    def quit(self) -> None:
        self.store.save()
        self._on_destroy()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = App(root)
    missing = app.images.missing
    if missing:
        messagebox.showwarning(
            "Pictures missing",
            "Some pictures could not be found.\n\n"
            "Run:  python3 tools/make_assets.py\n\n"
            f"First missing file:\n{missing[0]}",
        )
    root.mainloop()
