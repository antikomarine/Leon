"""Colour arithmetic, with no dependency on Tk.

Kept separate from :mod:`marasender.theme` so that the asset generator (which
runs without a window) can use the same contrast rules as the app.
"""

from __future__ import annotations


def mix(a: str, b: str, t: float) -> str:
    """Blend hex colours ``a`` and ``b``; ``t=0`` is ``a``, ``t=1`` is ``b``."""
    a, b = a.lstrip("#"), b.lstrip("#")
    parts = []
    for i in (0, 2, 4):
        av, bv = int(a[i : i + 2], 16), int(b[i : i + 2], 16)
        parts.append(round(av + (bv - av) * t))
    return "#%02x%02x%02x" % tuple(parts)


def luminance(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    r, g, b = (int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(a: str, b: str) -> float:
    """WCAG contrast ratio between two colours, from 1 (same) to 21 (black/white)."""
    la, lb = luminance(a), luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def is_dark(hex_color: str) -> bool:
    return luminance(hex_color) < 0.45


def readable(color: str, background: str, ratio: float = 4.5) -> str:
    """Lighten or darken ``color`` until it is readable on ``background``.

    Which way to move is decided by the background: on a dark background the
    colour is lifted towards white, on a light one it is pushed towards black.
    This is what lets every contact keep their own colour without any of them
    becoming hard to read in any of the palettes.
    """
    toward = "#ffffff" if is_dark(background) else "#000000"
    out = color
    for _ in range(24):
        if contrast_ratio(out, background) >= ratio:
            return out
        out = mix(out, toward, 0.12)
    return toward


def ink_for(background: str) -> str:
    """Pick white or near-black artwork for a coloured tile."""
    return "#ffffff" if contrast_ratio("#ffffff", background) >= 3.0 else "#16202b"


def text_ink(background: str, light: str = "#ffffff", dark: str = "#12181f") -> str:
    """Pick whichever of two inks reads better on ``background``.

    Half of the brand colours are light and half are dark, so no fixed rule
    ("white on colour") works: the choice is made per colour, by contrast.
    """
    return light if contrast_ratio(light, background) >= contrast_ratio(dark, background) else dark
