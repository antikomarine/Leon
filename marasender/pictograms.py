"""The picture vocabulary used by the picture board and by picture messages.

Each entry is one tile: a drawing (rendered to ``assets/pictograms/``), a text
label that is *always* shown next to the picture, and the sentence that gets
sent when the tile is chosen.  Keeping the metadata here means the asset
generator and the app can never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass

from .brand import (
    DEEP_MINT, DEEP_ORANGE, DEEP_PEACH, DEEP_SKY, DEEP_VIOLET,
    LIME, MINT, ORANGE, PEACH, SKY, VIOLET,
)
from .colorutil import ink_for


@dataclass(frozen=True)
class Pictogram:
    key: str
    label: str
    message: str
    color: str
    category: str


PICTOGRAMS: tuple[Pictogram, ...] = (
    # -- Answers ---------------------------------------------------------
    Pictogram("yes", "Yes", "Yes 👍", MINT, "Answers"),
    Pictogram("no", "No", "No 👎", ORANGE, "Answers"),
    Pictogram("maybe", "Maybe", "Maybe — I am not sure yet.", PEACH, "Answers"),
    Pictogram("thanks", "Thank you", "Thank you!", VIOLET, "Answers"),
    Pictogram("wait", "Please wait", "Please wait a moment.", SKY, "Answers"),
    Pictogram("again", "Say again", "Could you say that again, please?", LIME, "Answers"),
    # -- Needs -----------------------------------------------------------
    Pictogram("help", "Help", "I need help, please.", ORANGE, "Needs"),
    Pictogram("water", "Drink", "I would like something to drink.", SKY, "Needs"),
    Pictogram("food", "Food", "I would like something to eat.", PEACH, "Needs"),
    Pictogram("medicine", "Medicine", "I need my medicine.", VIOLET, "Needs"),
    Pictogram("bathroom", "Bathroom", "I need the bathroom.", DEEP_SKY, "Needs"),
    Pictogram("pain", "It hurts", "I am in pain.", DEEP_PEACH, "Needs"),
    Pictogram("sleep", "Rest", "I am tired and need to rest.", DEEP_VIOLET, "Needs"),
    Pictogram("stop", "Stop", "Please stop.", DEEP_ORANGE, "Needs"),
    # -- Feelings --------------------------------------------------------
    Pictogram("happy", "Happy", "I feel happy today 😊", LIME, "Feelings"),
    Pictogram("sad", "Sad", "I feel sad today.", DEEP_SKY, "Feelings"),
    Pictogram("love", "Love", "I love you ❤️", ORANGE, "Feelings"),
    Pictogram("question", "Question", "I have a question.", VIOLET, "Feelings"),
    # -- People & places -------------------------------------------------
    Pictogram("home", "Home", "I am at home.", MINT, "People & places"),
    Pictogram("family", "Family", "I am with my family.", DEEP_PEACH, "People & places"),
    Pictogram("doctor", "Doctor", "I need to see the doctor.", DEEP_ORANGE, "People & places"),
    Pictogram("work", "Work", "I am at work.", DEEP_SKY, "People & places"),
    Pictogram("car", "Travelling", "I am on my way.", SKY, "People & places"),
    Pictogram("walk", "Walking", "I am going for a walk.", DEEP_MINT, "People & places"),
    # -- Everyday --------------------------------------------------------
    Pictogram("phone", "Call me", "Please call me.", SKY, "Everyday"),
    Pictogram("music", "Music", "I am listening to music 🎵", VIOLET, "Everyday"),
    Pictogram("sun", "Nice weather", "The weather is lovely today ☀️", LIME, "Everyday"),
    Pictogram("rain", "Rain", "It is raining here 🌧️", DEEP_SKY, "Everyday"),
    Pictogram("book", "Reading", "I am reading a book.", DEEP_PEACH, "Everyday"),
    Pictogram("ball", "Playing", "I am playing a game ⚽", DEEP_MINT, "Everyday"),
)

BY_KEY: dict[str, Pictogram] = {p.key: p for p in PICTOGRAMS}


def glyph_ink(pictogram: Pictogram) -> str:
    """The colour the drawing on a tile is painted in."""
    return ink_for(pictogram.color)

CATEGORIES: tuple[str, ...] = tuple(dict.fromkeys(p.category for p in PICTOGRAMS))


def in_category(category: str) -> list[Pictogram]:
    return [p for p in PICTOGRAMS if p.category == category]
