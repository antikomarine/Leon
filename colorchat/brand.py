"""The six colours the whole app is built from.

Everything visible — contacts, message bubbles, picture tiles, the app bar,
the focus ring — is one of these six or a deeper version of one of them.
Change a value here and the entire app follows once the artwork is
regenerated with ``python3 tools/make_assets.py``.

Four of the six are light colours: they sing on a dark background and need
dark text or artwork on top. Nothing hard-codes that decision — the palettes
and :func:`colorchat.colorutil.text_ink` work it out from the colour itself.
"""

from __future__ import annotations

from .colorutil import contrast_ratio, mix, text_ink

ORANGE = "#FF4200"
MINT = "#47FF94"
VIOLET = "#7F2EFF"
SKY = "#62C7FF"
LIME = "#CBFF77"
PEACH = "#FFBA82"

BRAND: tuple[str, ...] = (ORANGE, MINT, VIOLET, SKY, LIME, PEACH)

NAMES: dict[str, str] = {
    ORANGE: "orange",
    MINT: "mint",
    VIOLET: "violet",
    SKY: "sky",
    LIME: "lime",
    PEACH: "peach",
}


def deep(color: str, amount: float = 0.5) -> str:
    """A darker member of the same family, for a second shade of one hue.

    Deepened a little further if needed, so that a label or a symbol drawn on
    top of it always clears the 4.5:1 contrast ratio.
    """
    out = mix(color, "#000000", amount)
    while contrast_ratio(text_ink(out), out) < 4.5:
        out = mix(out, "#000000", 0.06)
    return out


def soft(color: str, amount: float = 0.35) -> str:
    """A lighter member of the same family."""
    return mix(color, "#ffffff", amount)


DEEP_ORANGE = deep(ORANGE)
DEEP_MINT = deep(MINT)
DEEP_VIOLET = deep(VIOLET)
DEEP_SKY = deep(SKY)
DEEP_LIME = deep(LIME)
DEEP_PEACH = deep(PEACH)

DEEP: tuple[str, ...] = (
    DEEP_ORANGE, DEEP_MINT, DEEP_VIOLET, DEEP_SKY, DEEP_LIME, DEEP_PEACH,
)
