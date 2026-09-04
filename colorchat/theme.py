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

from .brand import DEEP_SKY, LIME, MINT, ORANGE, PEACH, SKY, VIOLET
from .colorutil import contrast_ratio, mix, readable, text_ink  # noqa: F401


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
    description="Daylight, with the brand colours at full strength",
    window="#f2eeea",
    bar=ORANGE,
    bar_text=text_ink(ORANGE),
    panel="#ffffff",
    panel_alt="#f4f0ec",
    canvas="#faf7f4",
    text="#17120f",
    text_soft="#5d5450",
    line="#d9cec7",
    accent=ORANGE,
    accent_text=text_ink(ORANGE),
    mine_bg=mix(MINT, "#ffffff", 0.62),
    mine_text="#0c2117",
    tick_read=DEEP_SKY,
    focus=VIOLET,
    tint=0.82,
    dark=False,
)

NIGHT = Palette(
    key="night",
    name="Night",
    description="Dark background — where these colours glow",
    window="#0d1014",
    bar=mix(ORANGE, "#000000", 0.68),
    bar_text=PEACH,
    panel="#171b21",
    panel_alt="#232a33",
    canvas="#11151a",
    text="#f1f4f7",
    text_soft="#a9b4c0",
    line="#333c48",
    accent=MINT,
    accent_text=text_ink(MINT),
    mine_bg=mix(MINT, "#0d1014", 0.78),
    mine_text="#e9fff3",
    tick_read=SKY,
    focus=LIME,
    tint=0.74,
    dark=True,
)

HIGH_CONTRAST = Palette(
    key="contrast",
    name="High contrast",
    description="Maximum contrast, thick outlines",
    window="#000000",
    bar="#000000",
    bar_text=LIME,
    panel="#000000",
    panel_alt="#181818",
    canvas="#000000",
    text="#ffffff",
    text_soft="#f0f0f0",
    line=LIME,
    accent=LIME,
    accent_text=text_ink(LIME),
    mine_bg=mix(MINT, "#000000", 0.82),
    mine_text="#ffffff",
    tick_read=SKY,
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
        return "light" if text_ink(on_color) == "#ffffff" else "dark"

    def icon_size(self) -> int:
        for size in (20, 26, 34):
            if size >= 18 * self.scale:
                return size
        return 34


def color_for_contrast(color: str) -> str:
    """Brighten a contact colour so it stays visible on pure black."""
    return readable(color, "#000000", 7.0)
