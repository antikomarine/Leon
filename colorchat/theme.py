"""Colours and fonts.

Three palettes ship with the app.  Every one of them keeps text and its
background at a comfortable contrast ratio, and every one keeps the *per
contact* colour coding that makes a busy conversation list easy to scan.

Nothing in the app hard-codes a colour: widgets ask the :class:`Theme` for one
and re-read it whenever the theme or the text size changes.
"""

from __future__ import annotations

import tkinter.font as tkfont
from dataclasses import dataclass
from typing import Callable

from .colorutil import contrast_ratio, is_dark, mix, readable  # noqa: F401


@dataclass(frozen=True)
class Palette:
    key: str
    name: str
    description: str
    window: str          # app background
    bar: str             # top app bar
    bar_text: str
    panel: str           # sidebar / composer background
    panel_alt: str       # hover / selected row
    canvas: str          # chat background
    text: str
    text_soft: str
    line: str            # separators and outlines
    accent: str          # primary action colour (send)
    accent_text: str
    mine_bg: str         # my own message bubble
    mine_text: str
    tick_read: str
    focus: str           # keyboard focus ring
    tint: float          # how far a contact colour is mixed towards the panel
    dark: bool


LIGHT = Palette(
    key="bright",
    name="Bright",
    description="Soft daylight colours",
    window="#e9eef3",
    bar="#0f766e",
    bar_text="#ffffff",
    panel="#ffffff",
    panel_alt="#eef3f7",
    canvas="#f4f7fa",
    text="#132029",
    text_soft="#526270",
    line="#c9d5df",
    accent="#0f766e",
    accent_text="#ffffff",
    mine_bg="#d6f2dd",
    mine_text="#0d2a18",
    tick_read="#1d6ff2",
    focus="#b8006e",
    tint=0.86,
    dark=False,
)

NIGHT = Palette(
    key="night",
    name="Night",
    description="Dark background, gentle on the eyes",
    window="#0f151b",
    bar="#123a35",
    bar_text="#eaf6f2",
    panel="#18212a",
    panel_alt="#22303c",
    canvas="#131c24",
    text="#eef4f8",
    text_soft="#a5b6c4",
    line="#31424f",
    accent="#1f9d76",
    accent_text="#04150f",
    mine_bg="#1f4d3d",
    mine_text="#eafaf2",
    tick_read="#5cc0ff",
    focus="#ffd54a",
    tint=0.72,
    dark=True,
)

HIGH_CONTRAST = Palette(
    key="contrast",
    name="High contrast",
    description="Maximum contrast, thick outlines",
    window="#000000",
    bar="#000000",
    bar_text="#ffe100",
    panel="#000000",
    panel_alt="#1c1c1c",
    canvas="#000000",
    text="#ffffff",
    text_soft="#e8e8e8",
    line="#ffe100",
    accent="#ffe100",
    accent_text="#000000",
    mine_bg="#003b1f",
    mine_text="#ffffff",
    tick_read="#57d1ff",
    focus="#ffffff",
    tint=0.0,
    dark=True,
)

PALETTES: tuple[Palette, ...] = (LIGHT, NIGHT, HIGH_CONTRAST)

BASE_SIZES = {
    "tiny": 9,
    "small": 10,
    "body": 12,
    "name": 12,
    "title": 15,
    "big": 18,
    "huge": 22,
}

TEXT_SCALES = (0.9, 1.0, 1.15, 1.3, 1.5, 1.75, 2.0)

PREFERRED_FAMILIES = (
    "Segoe UI", "SF Pro Text", "Helvetica Neue", "DejaVu Sans", "Noto Sans",
    "Liberation Sans", "Arial", "Helvetica",
)


class Theme:
    """Live theme state: palette, text scale and the fonts built from them."""

    def __init__(self, palette: Palette = LIGHT, scale_index: int = 1) -> None:
        self.palette = palette
        self.scale_index = scale_index
        self._listeners: list[Callable[[], None]] = []
        self.family = self._pick_family()
        self.fonts: dict[str, tkfont.Font] = {}
        self._build_fonts()

    # -- setup -------------------------------------------------------------
    def _pick_family(self) -> str:
        available = set(tkfont.families())
        for family in PREFERRED_FAMILIES:
            if family in available:
                return family
        return tkfont.nametofont("TkDefaultFont").cget("family")

    def _build_fonts(self) -> None:
        for name, size in BASE_SIZES.items():
            scaled = max(7, round(size * self.scale))
            weight = "bold" if name in ("name", "title", "big", "huge") else "normal"
            if name in self.fonts:
                self.fonts[name].configure(size=scaled, family=self.family, weight=weight)
            else:
                self.fonts[name] = tkfont.Font(family=self.family, size=scaled, weight=weight)
        if "body_bold" in self.fonts:
            self.fonts["body_bold"].configure(
                size=max(7, round(BASE_SIZES["body"] * self.scale)), family=self.family
            )
        else:
            self.fonts["body_bold"] = tkfont.Font(
                family=self.family,
                size=max(7, round(BASE_SIZES["body"] * self.scale)),
                weight="bold",
            )

    # -- state -------------------------------------------------------------
    @property
    def scale(self) -> float:
        return TEXT_SCALES[self.scale_index]

    def font(self, name: str) -> tkfont.Font:
        return self.fonts[name]

    def on_change(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def _notify(self) -> None:
        for callback in list(self._listeners):
            callback()

    def set_palette(self, palette: Palette) -> None:
        self.palette = palette
        self._notify()

    def next_palette(self) -> Palette:
        index = (PALETTES.index(self.palette) + 1) % len(PALETTES)
        self.set_palette(PALETTES[index])
        return self.palette

    def change_text_size(self, step: int) -> bool:
        new_index = min(len(TEXT_SCALES) - 1, max(0, self.scale_index + step))
        if new_index == self.scale_index:
            return False
        self.scale_index = new_index
        self._build_fonts()
        self._notify()
        return True

    # -- derived colours ---------------------------------------------------
    @property
    def p(self) -> Palette:
        return self.palette

    def contact_bubble(self, color: str) -> tuple[str, str, str]:
        """(background, outline, text) for a message received from a contact."""
        if self.p.key == "contrast":
            return "#000000", color_for_contrast(color), "#ffffff"
        if self.p.dark:
            return mix(color, self.p.panel, self.p.tint), mix(color, "#ffffff", 0.25), self.p.text
        return mix(color, "#ffffff", self.p.tint), mix(color, "#000000", 0.12), "#101a20"

    def chat_background(self, color: str) -> str:
        """The chat area is tinted with the contact's colour, very gently."""
        if self.p.key == "contrast":
            return self.p.canvas
        return mix(color, self.p.canvas, 0.94 if not self.p.dark else 0.90)

    def contact_ink(self, color: str) -> str:
        """A contact colour adjusted until it is readable on the panel."""
        target = 7.0 if self.p.key == "contrast" else 4.5
        return readable(color, self.p.panel, target)

    def row_selected(self, color: str) -> str:
        if self.p.key == "contrast":
            return "#1c1c1c"
        return mix(color, self.p.panel, 0.88 if not self.p.dark else 0.8)

    def icon_ink(self, on_color: str) -> str:
        """Pick the light or the dark icon variant for a given background."""
        return "light" if is_dark(on_color) else "dark"

    def icon_size(self) -> int:
        for size in (20, 26, 34):
            if size >= 18 * self.scale:
                return size
        return 34


def color_for_contrast(color: str) -> str:
    """Brighten a contact colour so it stays visible on pure black."""
    return readable(color, "#000000", 7.0)
