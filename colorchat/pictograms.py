"""The picture vocabulary used by the picture board and by picture messages.

Each entry is one tile: a drawing (rendered to ``assets/pictograms/``), a text
label that is *always* shown next to the picture, and the sentence that gets
sent when the tile is chosen.  Keeping the metadata here means the asset
generator and the app can never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass

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
    Pictogram("yes", "Yes", "Yes 👍", "#2e9e4f", "Answers"),
    Pictogram("no", "No", "No 👎", "#d1394b", "Answers"),
    Pictogram("maybe", "Maybe", "Maybe — I am not sure yet.", "#f0a020", "Answers"),
    Pictogram("thanks", "Thank you", "Thank you!", "#7a5cd6", "Answers"),
    Pictogram("wait", "Please wait", "Please wait a moment.", "#0b7fa8", "Answers"),
    Pictogram("again", "Say again", "Could you say that again, please?", "#c2571f", "Answers"),
    # -- Needs -----------------------------------------------------------
    Pictogram("help", "Help", "I need help, please.", "#e2542b", "Needs"),
    Pictogram("water", "Drink", "I would like something to drink.", "#1f8ecb", "Needs"),
    Pictogram("food", "Food", "I would like something to eat.", "#b8871b", "Needs"),
    Pictogram("medicine", "Medicine", "I need my medicine.", "#7a5cd6", "Needs"),
    Pictogram("bathroom", "Bathroom", "I need the bathroom.", "#0f8f8f", "Needs"),
    Pictogram("pain", "It hurts", "I am in pain.", "#c02f4a", "Needs"),
    Pictogram("sleep", "Rest", "I am tired and need to rest.", "#4b5cc4", "Needs"),
    Pictogram("stop", "Stop", "Please stop.", "#c62828", "Needs"),
    # -- Feelings --------------------------------------------------------
    Pictogram("happy", "Happy", "I feel happy today 😊", "#f2b705", "Feelings"),
    Pictogram("sad", "Sad", "I feel sad today.", "#4a6b8a", "Feelings"),
    Pictogram("love", "Love", "I love you ❤️", "#d6336c", "Feelings"),
    Pictogram("question", "Question", "I have a question.", "#5b6ad0", "Feelings"),
    # -- People & places -------------------------------------------------
    Pictogram("home", "Home", "I am at home.", "#2f8f5b", "People & places"),
    Pictogram("family", "Family", "I am with my family.", "#a3541f", "People & places"),
    Pictogram("doctor", "Doctor", "I need to see the doctor.", "#c0392b", "People & places"),
    Pictogram("work", "Work", "I am at work.", "#5a5f7a", "People & places"),
    Pictogram("car", "Travelling", "I am on my way.", "#2b6fbb", "People & places"),
    Pictogram("walk", "Walking", "I am going for a walk.", "#1f9e8a", "People & places"),
    # -- Everyday --------------------------------------------------------
    Pictogram("phone", "Call me", "Please call me.", "#3a7bd5", "Everyday"),
    Pictogram("music", "Music", "I am listening to music 🎵", "#8e44ad", "Everyday"),
    Pictogram("sun", "Nice weather", "The weather is lovely today ☀️", "#f09000", "Everyday"),
    Pictogram("rain", "Rain", "It is raining here 🌧️", "#4a7fa5", "Everyday"),
    Pictogram("book", "Reading", "I am reading a book.", "#8a6d3b", "Everyday"),
    Pictogram("ball", "Playing", "I am playing a game ⚽", "#2f7d4f", "Everyday"),
)

BY_KEY: dict[str, Pictogram] = {p.key: p for p in PICTOGRAMS}


def glyph_ink(pictogram: Pictogram) -> str:
    """The colour the drawing on a tile is painted in."""
    return ink_for(pictogram.color)

CATEGORIES: tuple[str, ...] = tuple(dict.fromkeys(p.category for p in PICTOGRAMS))


def in_category(category: str) -> list[Pictogram]:
    return [p for p in PICTOGRAMS if p.category == category]
