"""The conversation itself: rounded, colour-coded message bubbles on a canvas.

Bubbles are drawn rather than built from widgets, which is what makes the
rounded corners, the tails and the per-contact colours possible.  Everything is
laid out again whenever the window is resized or the text size changes, so
larger text always reflows instead of being clipped.
"""

from __future__ import annotations

import time
import tkinter as tk

from ..models import Chat, DELIVERED, Message, READ
from ..pictograms import BY_KEY as PICTOGRAM_BY_KEY
from ..theme import Theme, mix
from .scrollframe import bind_mousewheel

DAY = 86400


class ChatView(tk.Frame):
    def __init__(self, master: tk.Misc, app) -> None:
        self.app = app
        self.theme: Theme = app.theme
        super().__init__(master, background=self.theme.p.canvas)

        # A small requested height: the view expands to fill whatever is left,
        # and never demands space that the composer needs.
        self.canvas = tk.Canvas(
            self, background=self.theme.p.canvas, highlightthickness=0, borderwidth=0,
            height=120,
        )
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.chat: Chat | None = None
        self.typing = False
        self.selected: Message | None = None
        self._images: list = []          # keep Tk images alive while displayed
        self._resize_job: str | None = None
        self._last_width = 0
        self._bubbles: list[tuple[str, Message]] = []

        self.canvas.bind("<Configure>", self._on_resize)
        bind_mousewheel(self.canvas, self.canvas)
        self.canvas.bind("<Button-1>", self._on_click, add="+")
        self.bind("<Destroy>", self._cancel_resize, add="+")

    # -- public API --------------------------------------------------------
    def show(self, chat: Chat | None, scroll_to_end: bool = True) -> None:
        self.chat = chat
        self.selected = None
        self.render(scroll_to_end=scroll_to_end)

    def set_typing(self, typing: bool) -> None:
        if self.typing != typing:
            self.typing = typing
            self.render(scroll_to_end=True)

    def refresh(self) -> None:
        self.render(scroll_to_end=False)

    def scroll_to_end(self) -> None:
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def select_last(self) -> Message | None:
        if self.chat and self.chat.messages:
            self.selected = self.chat.messages[-1]
            self.render(scroll_to_end=True)
            return self.selected
        return None

    # -- drawing -----------------------------------------------------------
    def render(self, scroll_to_end: bool = False) -> None:
        canvas, theme = self.canvas, self.theme
        canvas.delete("all")
        self._images.clear()
        self._bubbles.clear()

        width = max(360, canvas.winfo_width())
        self._last_width = width
        if self.chat is None:
            self._draw_empty(width)
            return

        person = self.chat.person
        background = theme.chat_background(person.color)
        canvas.configure(background=background)
        self.configure(background=background)

        y = 16
        previous_day = None
        for message in self.chat.messages:
            day = time.strftime("%Y-%m-%d", time.localtime(message.ts))
            if day != previous_day:
                y = self._draw_day_divider(width, y, message.ts)
                previous_day = day
            y = self._draw_bubble(width, y, message)

        if self.typing:
            y = self._draw_typing(width, y)

        canvas.configure(scrollregion=(0, 0, width, y + 12))
        if scroll_to_end:
            self.scroll_to_end()

    def _draw_empty(self, width: int) -> None:
        palette = self.theme.p
        self.canvas.create_text(
            width / 2, 140, text="Choose a conversation on the left to start reading.",
            font=self.theme.font("title"), fill=palette.text_soft, width=width - 80,
            justify="center",
        )

    def _round_rect(self, x0, y0, x1, y1, r, **kwargs):
        r = max(2, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
        points = [
            x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
            x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_day_divider(self, width: int, y: int, ts: float) -> int:
        palette = self.theme.p
        label = friendly_day(ts)
        font = self.theme.font("small")
        text_id = self.canvas.create_text(
            width / 2, y + 12, text=label, font=font, fill=palette.text_soft
        )
        x0, y0, x1, y1 = self.canvas.bbox(text_id)
        pill = self._round_rect(
            x0 - 12, y0 - 5, x1 + 12, y1 + 5, 12,
            fill=palette.panel, outline=palette.line, width=1,
        )
        self.canvas.tag_lower(pill, text_id)
        return y + 34

    def _draw_bubble(self, width: int, y: int, message: Message) -> int:
        canvas, theme, palette = self.canvas, self.theme, self.theme.p
        mine = message.mine
        sender = self.app.person_for(message.sender)
        avatar_size = max(36, min(56, round(30 * theme.scale)))
        gutter = 16
        avatar_gap = avatar_size + 10

        if mine:
            fill = palette.mine_bg
            outline = mix(palette.accent, "#000000", 0.1)
            ink = palette.mine_text
        else:
            fill, outline, ink = theme.contact_bubble(sender.color)

        max_bubble = min(width - gutter * 2 - avatar_gap, max(280, int(width * 0.68)))
        pad = 12
        inner_width = max_bubble - pad * 2

        parts: list[int] = []
        content_height = 0
        content_width = 0

        show_name = self.chat is not None and self.chat.key == "family" and not mine
        if show_name:
            name_id = canvas.create_text(
                -5000, 0, anchor="nw", text=sender.name, font=theme.font("body_bold"),
                fill=theme.contact_ink(sender.color),
            )
            parts.append(name_id)
            bounds = canvas.bbox(name_id)
            content_width = max(content_width, bounds[2] - bounds[0])
            content_height += bounds[3] - bounds[1] + 4

        picture_id = None
        if message.picture:
            big = not message.text.strip()
            image = self.app.images.pictogram(message.picture, 128 if big else 64)
            if image is not None:
                self._images.append(image)
                picture_id = canvas.create_image(-5000, 0, anchor="nw", image=image)
                parts.append(picture_id)
                content_width = max(content_width, image.width())
                content_height += image.height() + 6
            known = message.picture in PICTOGRAM_BY_KEY
            caption = PICTOGRAM_BY_KEY[message.picture].label if known else ""
            if caption:
                caption_id = canvas.create_text(
                    -5000, 0, anchor="nw", text=caption, font=theme.font("body_bold"), fill=ink,
                )
                parts.append(caption_id)
                bounds = canvas.bbox(caption_id)
                content_width = max(content_width, bounds[2] - bounds[0])
                content_height += bounds[3] - bounds[1] + 4

        text_id = None
        if message.text.strip():
            text_id = canvas.create_text(
                -5000, 0, anchor="nw", text=message.text, font=theme.font("body"),
                fill=ink, width=inner_width,
            )
            parts.append(text_id)
            bounds = canvas.bbox(text_id)
            content_width = max(content_width, bounds[2] - bounds[0])
            content_height += bounds[3] - bounds[1]

        stamp = time.strftime("%H:%M", time.localtime(message.ts))
        meta_id = canvas.create_text(
            -5000, 0, anchor="nw", text=stamp, font=theme.font("tiny"),
            fill=mix(ink, fill, 0.35),
        )
        parts.append(meta_id)
        meta_bounds = canvas.bbox(meta_id)
        meta_width = meta_bounds[2] - meta_bounds[0]
        meta_height = meta_bounds[3] - meta_bounds[1]

        tick_image = None
        if mine:
            ink_name = "read" if message.status == READ else theme.icon_ink(fill)
            if message.status == READ and palette.key == "contrast":
                ink_name = "read_bright"
            icon_name = "tick_read" if message.status in (READ, DELIVERED) else "tick_sent"
            tick_image = self.app.images.icon(icon_name, ink_name, 20)
            if tick_image is not None:
                self._images.append(tick_image)
                meta_width += tick_image.width() + 4

        bubble_width = max(120, min(max_bubble, max(content_width, meta_width) + pad * 2))
        bubble_height = content_height + meta_height + pad * 2 + 2

        if mine:
            x1 = width - gutter
            x0 = x1 - bubble_width
        else:
            x0 = gutter + avatar_gap
            x1 = x0 + bubble_width

        radius = 16
        bubble = self._round_rect(
            x0, y, x1, y + bubble_height, radius,
            fill=fill, outline=outline, width=2 if palette.key != "contrast" else 3,
        )
        tail = canvas.create_polygon(
            (x1, y + 8, x1 + 9, y + 2, x1 - 2, y + 24) if mine
            else (x0, y + 8, x0 - 9, y + 2, x0 + 2, y + 24),
            fill=fill, outline=outline, width=1,
        )

        if self.selected is message:
            self._round_rect(
                x0 - 4, y - 4, x1 + 4, y + bubble_height + 4, radius + 4,
                fill="", outline=palette.focus, width=3,
            )

        cursor_y = y + pad
        for item in parts:
            if item == meta_id:
                continue                      # the time stamp is placed separately
            canvas.coords(item, x0 + pad, cursor_y)
            top, bottom = canvas.bbox(item)[1], canvas.bbox(item)[3]
            cursor_y += (bottom - top) + (6 if item == picture_id else 4)

        meta_x = x1 - pad - (tick_image.width() + 4 if tick_image is not None else 0)
        canvas.coords(
            meta_id,
            meta_x - (meta_bounds[2] - meta_bounds[0]),
            y + bubble_height - pad - meta_height,
        )
        if tick_image is not None:
            tick_id = canvas.create_image(
                x1 - pad, y + bubble_height - pad - meta_height / 2,
                anchor="e", image=tick_image,
            )
            parts.append(tick_id)

        if not mine:
            avatar = self.app.images.avatar(sender.key, avatar_size)
            if avatar is not None:
                self._images.append(avatar)
                canvas.create_image(gutter, y + bubble_height - avatar.height(),
                                    anchor="nw", image=avatar)

        tag = f"bubble:{message.id}"
        for item in [bubble, tail, *parts]:
            canvas.itemconfigure(item, tags=(tag,))
        self._bubbles.append((tag, message))
        canvas.tag_raise(tail, bubble)
        for item in parts:
            canvas.tag_raise(item)

        return y + bubble_height + 14

    def _draw_typing(self, width: int, y: int) -> int:
        theme = self.theme
        person = self.chat.person
        fill, outline, ink = theme.contact_bubble(person.color)
        text = f"{person.name.split()[0]} is typing…"
        text_id = self.canvas.create_text(
            80, y + 16, anchor="w", text=text, font=theme.font("body"), fill=ink
        )
        x0, y0, x1, y1 = self.canvas.bbox(text_id)
        bubble = self._round_rect(x0 - 14, y0 - 8, x1 + 14, y1 + 8, 14,
                                  fill=fill, outline=outline, width=2)
        self.canvas.tag_lower(bubble, text_id)
        avatar = self.app.images.avatar(person.key, 44)
        if avatar is not None:
            self._images.append(avatar)
            self.canvas.create_image(16, y0 - 6, anchor="nw", image=avatar)
        return y1 + 24

    # -- events ------------------------------------------------------------
    def _cancel_resize(self, _event=None) -> None:
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
            self._resize_job = None

    def _on_resize(self, event) -> None:
        if abs(event.width - self._last_width) < 8:
            return
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(80, lambda: self.render(scroll_to_end=False))

    def _on_click(self, event) -> None:
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        hits = set(self.canvas.find_overlapping(x - 1, y - 1, x + 1, y + 1))
        for tag, message in self._bubbles:
            if hits & set(self.canvas.find_withtag(tag)):
                self.selected = message
                self.render(scroll_to_end=False)
                self.app.on_message_selected(message)
                return


def friendly_day(ts: float) -> str:
    today = time.localtime()
    that_day = time.localtime(ts)
    same = (today.tm_year, today.tm_yday) == (that_day.tm_year, that_day.tm_yday)
    if same:
        return "Today"
    yesterday = time.localtime(time.time() - DAY)
    if (yesterday.tm_year, yesterday.tm_yday) == (that_day.tm_year, that_day.tm_yday):
        return "Yesterday"
    if time.time() - ts < 6 * DAY:
        return time.strftime("%A", that_day)
    return time.strftime("%d %B %Y", that_day)
