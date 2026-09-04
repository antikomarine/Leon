"""A scrollable container: a canvas with a normal frame inside it."""

from __future__ import annotations

import tkinter as tk


class ScrollFrame(tk.Frame):
    def __init__(self, master, background: str, **kwargs) -> None:
        super().__init__(master, background=background, **kwargs)
        self.canvas = tk.Canvas(
            self, background=background, highlightthickness=0, borderwidth=0, takefocus=False
        )
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.body = tk.Frame(self.canvas, background=background)
        self._window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")

        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        bind_mousewheel(self.canvas, self.canvas)
        bind_mousewheel(self.body, self.canvas)

    def _on_scroll(self, first: str, last: str) -> None:
        # Hide the scrollbar when everything already fits.
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.scrollbar.grid_remove()
        else:
            self.scrollbar.grid()
        self.scrollbar.set(first, last)

    def _on_body_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)

    def set_background(self, color: str) -> None:
        self.configure(background=color)
        self.canvas.configure(background=color)
        self.body.configure(background=color)

    def scroll_to_top(self) -> None:
        self.canvas.yview_moveto(0.0)


def bind_mousewheel(widget: tk.Misc, canvas: tk.Canvas) -> None:
    """Wheel scrolling for every platform, including children added later."""

    def on_wheel(event) -> str:
        if event.num == 4:
            canvas.yview_scroll(-3, "units")
        elif event.num == 5:
            canvas.yview_scroll(3, "units")
        elif event.delta:
            step = -1 if event.delta > 0 else 1
            canvas.yview_scroll(step * 3, "units")
        return "break"

    for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        widget.bind(sequence, on_wheel, add="+")


def bind_wheel_recursive(widget: tk.Misc, canvas: tk.Canvas) -> None:
    bind_mousewheel(widget, canvas)
    for child in widget.winfo_children():
        bind_wheel_recursive(child, canvas)
