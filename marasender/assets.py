"""Loading the generated PNGs into Tk images.

Tk drops an image as soon as nothing references it, so every image is cached
here for the lifetime of the app.
"""

from __future__ import annotations

import os
import tkinter as tk

ASSET_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

AVATAR_SIZES = (44, 96)
PICTOGRAM_SIZES = (64, 128)
ICON_SIZES = (20, 26, 34)
WORDMARK_HEIGHTS = (26, 32, 40, 52, 64)


def _closest(wanted: int, available: tuple[int, ...]) -> int:
    return min(available, key=lambda size: abs(size - wanted))


class Images:
    """Cache of every picture the interface shows."""

    def __init__(self, root: str = ASSET_ROOT) -> None:
        self.root = root
        self._cache: dict[str, tk.PhotoImage] = {}
        self.missing: list[str] = []

    def _load(self, *parts: str) -> tk.PhotoImage | None:
        path = os.path.join(self.root, *parts)
        if path in self._cache:
            return self._cache[path]
        if not os.path.exists(path):
            if path not in self.missing:
                self.missing.append(path)
            return None
        image = tk.PhotoImage(file=path)
        self._cache[path] = image
        return image

    def avatar(self, key: str, size: int = 44) -> tk.PhotoImage | None:
        return self._load("avatars", f"{key}_{_closest(size, AVATAR_SIZES)}.png")

    def pictogram(self, key: str, size: int = 64) -> tk.PhotoImage | None:
        return self._load("pictograms", f"{key}_{_closest(size, PICTOGRAM_SIZES)}.png")

    def icon(self, name: str, ink: str = "dark", size: int = 26) -> tk.PhotoImage | None:
        return self._load("icons", f"{name}_{ink}_{_closest(size, ICON_SIZES)}.png")

    def wordmark(self, height: int = 32) -> tk.PhotoImage | None:
        """The drawn app name, used when Bauhaus 93 is not installed."""
        return self._load("wordmark", f"wordmark_{_closest(height, WORDMARK_HEIGHTS)}.png")
