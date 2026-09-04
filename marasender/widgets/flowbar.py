"""A row of buttons that wraps onto extra lines when it runs out of room.

The app bar holds the accessibility controls, and those controls grow with the
text size -- at 200% they simply do not fit on one line.  Rather than clipping
them (or dropping their words, which would leave picture-only buttons), the bar
flows onto as many lines as it needs.
"""

from __future__ import annotations

import tkinter as tk


class FlowBar(tk.Frame):
    def __init__(self, master: tk.Misc, align: str = "right", gap: int = 6,
                 pad: int = 8, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self.items: list[tk.Widget] = []
        self.align, self.gap, self.pad = align, gap, pad
        self._pending: str | None = None
        self.bind("<Configure>", lambda _e: self.reflow())
        self.bind("<Destroy>", self._cancel, add="+")

    def _cancel(self, _event=None) -> None:
        if self._pending is not None:
            try:
                self.after_cancel(self._pending)
            except Exception:
                pass
            self._pending = None

    def reflow_soon(self) -> None:
        self._cancel()
        self._pending = self.after_idle(self.reflow)

    def add(self, widget: tk.Widget) -> tk.Widget:
        self.items.append(widget)
        return widget

    def reflow(self) -> None:
        self._pending = None
        if not self.items or not self.winfo_exists():
            return
        width = self.winfo_width()
        if width <= 1:
            self.reflow_soon()
            return
        rows: list[list[tk.Widget]] = [[]]
        used = 0
        for widget in self.items:
            needed = widget.winfo_reqwidth() + self.gap
            if rows[-1] and used + needed > width - self.pad * 2:
                rows.append([])
                used = 0
            rows[-1].append(widget)
            used += needed

        y = self.pad
        for row in rows:
            total = sum(w.winfo_reqwidth() for w in row) + self.gap * (len(row) - 1)
            x = width - self.pad - total if self.align == "right" else self.pad
            height = max(w.winfo_reqheight() for w in row)
            for widget in row:
                widget.place(x=x, y=y)
                x += widget.winfo_reqwidth() + self.gap
            y += height + self.gap
        self.configure(height=y - self.gap + self.pad)
