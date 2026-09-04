"""Messages, chats and the little JSON store that keeps them between runs."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Iterable

from . import people
from .pictograms import BY_KEY as PICTOGRAM_BY_KEY

SENT, DELIVERED, READ = "sent", "delivered", "read"


def data_dir() -> str:
    """Where the conversation history lives (override with $MARASENDER_HOME)."""
    override = os.environ.get("MARASENDER_HOME")
    if override:
        return override
    return os.path.join(os.path.expanduser("~"), ".marasender")


@dataclass
class Message:
    sender: str                     # "me" or a contact key
    text: str = ""
    picture: str | None = None      # a pictogram key, shown above the text
    ts: float = field(default_factory=time.time)
    status: str = READ              # only meaningful for messages I sent
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    @property
    def mine(self) -> bool:
        return self.sender == "me"

    def preview(self) -> str:
        if self.picture and self.picture in PICTOGRAM_BY_KEY:
            label = PICTOGRAM_BY_KEY[self.picture].label
            return f"[{label}] {self.text}".strip()
        return self.text

    def spoken(self) -> str:
        who = "You said" if self.mine else f"{people.get(self.sender).name} said"
        return f"{who}: {self.preview()}"


@dataclass
class Chat:
    key: str                        # the contact key this conversation is with
    messages: list[Message] = field(default_factory=list)
    unread: int = 0
    muted: bool = False
    pinned: bool = False

    @property
    def person(self) -> people.Person:
        return people.get(self.key)

    def last(self) -> Message | None:
        return self.messages[-1] if self.messages else None

    def add(self, message: Message) -> Message:
        self.messages.append(message)
        if not message.mine:
            self.unread += 1
        return message

    def mark_read(self) -> None:
        self.unread = 0
        for message in self.messages:
            if message.mine and message.status != READ:
                message.status = READ

    def search(self, needle: str) -> list[Message]:
        needle = needle.lower()
        return [m for m in self.messages if needle in m.preview().lower()]


class Store:
    """All conversations, persisted as one small JSON file."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or os.path.join(data_dir(), "chats.json")
        self.chats: dict[str, Chat] = {}
        self.load()

    # -- persistence -------------------------------------------------------
    def load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (OSError, ValueError):
            self.chats = seed_chats()
            self.save()
            return
        chats: dict[str, Chat] = {}
        for key, blob in raw.get("chats", {}).items():
            if key not in people.BY_KEY:
                continue          # a contact that no longer exists
            chats[key] = Chat(
                key=key,
                messages=[Message(**m) for m in blob.get("messages", [])],
                unread=blob.get("unread", 0),
                muted=blob.get("muted", False),
                pinned=blob.get("pinned", False),
            )
        for person in people.CONTACTS:     # keep new contacts visible
            chats.setdefault(person.key, Chat(key=person.key))
        self.chats = chats

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        blob = {
            "version": 1,
            "chats": {
                key: {
                    "messages": [asdict(m) for m in chat.messages],
                    "unread": chat.unread,
                    "muted": chat.muted,
                    "pinned": chat.pinned,
                }
                for key, chat in self.chats.items()
            },
        }
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(blob, handle, indent=1)
        os.replace(tmp, self.path)

    def reset(self) -> None:
        """Throw the history away and start again from the demo conversations."""
        self.chats = seed_chats()
        self.save()

    # -- queries -----------------------------------------------------------
    def ordered(self) -> list[Chat]:
        """Pinned first, then most recent activity first."""
        def sort_key(chat: Chat):
            last = chat.last()
            return (0 if chat.pinned else 1, -(last.ts if last else 0))

        return sorted(self.chats.values(), key=sort_key)

    def matching(self, needle: str) -> list[Chat]:
        needle = needle.strip().lower()
        if not needle:
            return self.ordered()
        out = []
        for chat in self.ordered():
            if needle in chat.person.name.lower() or chat.search(needle):
                out.append(chat)
        return out

    def total_unread(self) -> int:
        return sum(chat.unread for chat in self.chats.values())


# ---------------------------------------------------------------------------
# Demo history, so the app has something to show the first time it is opened.
# ---------------------------------------------------------------------------
MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR

SEED: dict[str, Iterable[tuple[str, str, str | None, float]]] = {
    "amina": (
        ("amina", "Morning! Did you sleep alright?", None, 2 * DAY + 3 * HOUR),
        ("me", "Not bad at all, thank you.", None, 2 * DAY + 2.8 * HOUR),
        ("amina", "I took the dog to the park, the weather was perfect.", "sun",
         2 * DAY + 2 * HOUR),
        ("me", "", "happy", 26 * HOUR),
        ("amina", "That smile made my day 😊 Coffee on Friday?", None, 25 * HOUR),
        ("me", "Yes please, 10am at the usual place.", None, 24 * HOUR),
        ("amina", "Perfect. I will pick you up.", None, 23.5 * HOUR),
    ),
    "luca": (
        ("luca", "Parcel arrived for you, I put it inside.", None, 5 * HOUR),
        ("me", "Thank you!", "thanks", 4.5 * HOUR),
        ("luca", "No trouble. Dog walk at six if you fancy it.", None, 4 * HOUR),
    ),
    "priya": (
        ("priya", "Guess who is making lasagne tonight 🍝", "food", 30 * HOUR),
        ("me", "Save me a plate!", None, 29 * HOUR),
        ("priya", "Already done. Mum says hello.", None, 28 * HOUR),
    ),
    "tom": (
        ("tom", "Bluebird review moved to Thursday 14:00.", None, 8 * HOUR),
        ("me", "Noted, I will have the numbers ready.", None, 7.6 * HOUR),
        ("tom", "Great, thanks. No rush on the slides.", None, 7 * HOUR),
    ),
    "grace": (
        ("grace", "Good morning! How are you feeling today?", None, 3 * HOUR),
        ("me", "", "happy", 2.6 * HOUR),
        ("grace", "Wonderful. I will be with you at eleven.", "wait", 2.4 * HOUR),
    ),
    "kenji": (
        ("kenji", "New record shop opened by the station 🎵", "music", 3 * DAY),
        ("me", "We have to go.", None, 3 * DAY - HOUR),
    ),
    "hana": (
        ("hana", "Your results are all normal. Nothing to worry about.", None, 4 * DAY),
        ("me", "That is a relief, thank you doctor.", None, 4 * DAY - 0.5 * HOUR),
        ("hana", "Repeat prescription is ready at the pharmacy.", "medicine", 20 * HOUR),
    ),
    "family": (
        ("priya", "Sunday lunch at Mum's, one o'clock!", None, 12 * HOUR),
        ("amina", "I will bring the pudding.", None, 11.5 * HOUR),
        ("me", "Count me in.", "yes", 11 * HOUR),
    ),
}


def seed_chats() -> dict[str, Chat]:
    now = time.time()
    chats: dict[str, Chat] = {}
    for person in people.CONTACTS:
        chat = Chat(key=person.key)
        for sender, text, picture, ago in SEED.get(person.key, ()):
            chat.add(Message(sender=sender, text=text, picture=picture, ts=now - ago))
        chat.unread = 0
        chats[person.key] = chat
    chats["grace"].unread = 1
    chats["luca"].unread = 2
    chats["amina"].pinned = True
    return chats
