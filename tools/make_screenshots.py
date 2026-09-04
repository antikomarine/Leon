#!/usr/bin/env python3
"""Take the screenshots used in the README.

Developer tool, not needed to run the app.  It needs Pillow and a display; on a
headless machine run it through Xvfb::

    xvfb-run -a -s "-screen 0 1280x820x24" python3 tools/make_screenshots.py
"""

from __future__ import annotations

import os
import sys
import tkinter as tk

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("COLORCHAT_HOME", os.path.join("/tmp", "colorchat-screenshots"))

from PIL import ImageGrab  # noqa: E402

from colorchat.app import App  # noqa: E402
from colorchat.pictograms import BY_KEY  # noqa: E402

OUT = os.path.join(ROOT, "docs", "screenshots")
WINDOW = (0, 0, 1220, 780)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    root = tk.Tk()
    app = App(root)

    def shot(name: str) -> None:
        root.update_idletasks()
        root.update()
        image = ImageGrab.grab(xdisplay=os.environ.get("DISPLAY")).crop(WINDOW)
        image.save(os.path.join(OUT, f"{name}.png"))
        print("wrote", name)

    steps = [
        lambda: app.open_chat("amina"),
        lambda: shot("bright"),
        lambda: app.open_chat("grace"),
        lambda: app.open_board(),
        lambda: shot("picture-board"),
        lambda: app.send_pictogram(BY_KEY["help"]),
        lambda: app.close_board(),
        lambda: None,
        lambda: None,
        lambda: app.cycle_palette(),
        lambda: shot("night"),
        lambda: app.cycle_palette(),
        lambda: app.change_text_size(2),
        lambda: shot("high-contrast-large-text"),
    ]

    def run(index: int = 0) -> None:
        if index >= len(steps):
            root.after(200, root.destroy)
            return
        steps[index]()
        root.after(700, lambda: run(index + 1))

    root.after(900, run)
    root.mainloop()


if __name__ == "__main__":
    main()
