"""Small text helpers shared by the widgets."""

from __future__ import annotations


def elide(text: str, font, max_pixels: int) -> str:
    """Shorten text with an ellipsis so it never overruns its column."""
    if max_pixels <= 0 or font.measure(text) <= max_pixels:
        return text
    while text and font.measure(text + "…") > max_pixels:
        text = text[:-1]
    return text.rstrip() + "…"
