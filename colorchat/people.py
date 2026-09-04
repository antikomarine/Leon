"""The people in the address book.

Every person carries their own colour *and* their own badge shape.  The badge
matters: colour alone is not an accessible way to tell contacts apart, so each
contact is also identifiable by the shape stamped on their avatar and shown
next to their name.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Person:
    key: str
    name: str
    color: str          # the contact's signature colour
    badge: str          # shape stamped on the avatar: a colour-free identifier
    style: int          # which avatar illustration to draw
    about: str          # status line under the name
    persona: str        # which reply style the simulated contact uses


ME = Person(
    key="me",
    name="You",
    color="#0f766e",
    badge="circle",
    style=0,
    about="This is you",
    persona="me",
)

CONTACTS: tuple[Person, ...] = (
    Person("amina", "Amina Yusuf", "#d6336c", "heart", 1,
           "Best friend · loves photos", "warm"),
    Person("luca", "Luca Rossi", "#2f7d4f", "square", 2,
           "Neighbour · walks the dog at 6", "practical"),
    Person("priya", "Priya Nair", "#b8871b", "triangle", 3,
           "Sister · always hungry", "playful"),
    Person("tom", "Tom Becker", "#2b6fbb", "star", 4,
           "Work · project Bluebird", "practical"),
    Person("grace", "Grace Okafor", "#7a5cd6", "diamond", 5,
           "Support worker · weekdays 9–5", "carer"),
    Person("kenji", "Kenji Sato", "#c2571f", "hexagon", 6,
           "Music club · Thursday nights", "playful"),
    Person("hana", "Dr. Hana Fischer", "#c0392b", "plus", 7,
           "Clinic · replies within a day", "carer"),
    Person("family", "Family group", "#5a5f7a", "group", 8,
           "Mum, Dad, Priya and you", "warm"),
)

BY_KEY: dict[str, Person] = {p.key: p for p in (ME, *CONTACTS)}

BADGE_NAMES: dict[str, str] = {
    "circle": "circle",
    "square": "square",
    "triangle": "triangle",
    "star": "star",
    "diamond": "diamond",
    "heart": "heart",
    "hexagon": "hexagon",
    "plus": "cross",
    "group": "group",
}


def get(key: str) -> Person:
    return BY_KEY[key]
