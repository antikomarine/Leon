"""Buttons drawn from frames and labels.

Tk's own button ignores background colours on macOS, and the whole point of
this app is colour, so buttons are built by hand.  Every button:

* shows a picture *and* a word -- never an icon on its own,
* takes keyboard focus and draws a thick focus ring,
* reacts to hover and to being pressed,
* has a tooltip with the same wording as its label.
"""

from __future__ import annotations

import tkinter as tk

from ..theme import Theme, is_dark, mix


class Tooltip:
    def __init__(self, widget: tk.Misc, text: str, theme: Theme) -> None:
        self.widget, self.text, self.theme = widget, text, theme
        self.window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")
        widget.bind("<Destroy>", self.hide, add="+")
        self._after: str | None = None

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._after = self.widget.after(600, self.show)

    def _cancel(self) -> None:
        if self._after is not None:
            try:
                self.widget.after_cancel(self._after)
            except Exception:
                pass
            self._after = None

    def show(self) -> None:
        if self.window or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(f"+{x}+{y}")
        palette = self.theme.p
        tk.Label(
            self.window, text=self.text, justify="left",
            background=palette.text, foreground=palette.panel,
            font=self.theme.font("small"), padx=8, pady=4,
        ).pack()

    def hide(self, _event=None) -> None:
        self._cancel()
        if self.window is not None:
            self.window.destroy()
            self.window = None


class ColorButton(tk.Frame):
    """A clickable picture-and-word button."""

    def __init__(
        self,
        master: tk.Misc,
        theme: Theme,
        text: str,
        command=None,
        image=None,
        style: str = "solid",          # solid | ghost | quiet
        color: str | None = None,      # overrides the palette accent
        tooltip: str | None = None,
        compact: bool = False,
        font_key: str = "body",
    ) -> None:
        super().__init__(master, takefocus=True, highlightthickness=3, cursor="hand2")
        self.theme = theme
        self.style = style
        self.color = color
        self.command = command
        self.compact = compact
        self.font_key = font_key
        self._pressed = False
        self._hover = False
        self.enabled = True

        pad = 4 if compact else 7
        self.icon = tk.Label(self, image=image, borderwidth=0)
        self.icon.image = image
        self.label = tk.Label(self, text=text, borderwidth=0)
        if image is not None:
            self.icon.pack(side="left", padx=(pad + 2, 0), pady=pad)
        if text:
            left = 6 if image is not None else pad + 2
            self.label.pack(side="left", padx=(left, pad + 2), pady=pad)

        for widget in (self, self.icon, self.label):
            widget.bind("<Button-1>", self._on_press, add="+")
            widget.bind("<ButtonRelease-1>", self._on_release, add="+")
            widget.bind("<Enter>", self._on_enter, add="+")
            widget.bind("<Leave>", self._on_leave, add="+")
        self.bind("<Return>", self._activate, add="+")
        self.bind("<space>", self._activate, add="+")
        self.bind("<FocusIn>", lambda _e: self.refresh(), add="+")
        self.bind("<FocusOut>", lambda _e: self.refresh(), add="+")

        self.tip = Tooltip(self, tooltip or text, theme)
        theme.on_change(self._safe_refresh)
        self.refresh()

    # -- appearance --------------------------------------------------------
    def _colors(self) -> tuple[str, str]:
        palette = self.theme.p
        if self.style == "solid":
            base = self.color or palette.accent
            fg = "#ffffff" if is_dark(base) else "#10181f"
            if palette.key == "contrast":
                base, fg = palette.accent, palette.accent_text
        elif self.style == "ghost":
            base = palette.panel
            fg = self.color or palette.text
            if palette.key == "contrast":
                fg = palette.text
        else:  # quiet: sits on the coloured app bar
            base = palette.bar
            fg = palette.bar_text
        if not self.enabled:
            return mix(base, palette.panel, 0.6), palette.text_soft
        if self._pressed:
            base = mix(base, "#000000", 0.18)
        elif self._hover:
            base = mix(base, "#ffffff" if is_dark(base) else "#000000", 0.12)
        return base, fg

    def refresh(self) -> None:
        background, foreground = self._colors()
        palette = self.theme.p
        focused = self.focus_get() is self
        ring = palette.focus if focused else background
        self.configure(background=background, highlightbackground=ring, highlightcolor=ring)
        self.icon.configure(background=background)
        self.label.configure(
            background=background, foreground=foreground, font=self.theme.font(self.font_key)
        )

    def _safe_refresh(self) -> None:
        if self.winfo_exists():
            self.refresh()

    def set_image(self, image) -> None:
        self.icon.configure(image=image)
        self.icon.image = image

    def set_text(self, text: str) -> None:
        self.label.configure(text=text)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "")
        self.refresh()

    # -- interaction -------------------------------------------------------
    def _on_enter(self, _event=None) -> None:
        self._hover = True
        self.refresh()

    def _on_leave(self, _event=None) -> None:
        self._hover = self._pressed = False
        self.refresh()

    def _on_press(self, _event=None) -> None:
        if not self.enabled:
            return
        self._pressed = True
        self.focus_set()
        self.refresh()

    def _on_release(self, event=None) -> None:
        was_pressed, self._pressed = self._pressed, False
        self.refresh()
        if was_pressed and self.enabled:
            inside = (
                0 <= event.x_root - self.winfo_rootx() <= self.winfo_width()
                and 0 <= event.y_root - self.winfo_rooty() <= self.winfo_height()
            ) if event is not None else True
            if inside:
                self._activate()

    def _activate(self, _event=None) -> str:
        if self.enabled and self.command is not None:
            self.tip.hide()
            self.command()
        return "break"
