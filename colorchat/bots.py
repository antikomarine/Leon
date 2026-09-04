"""Replies from the simulated contacts.

The app is a self-contained demo: there is no server and no account, so the
people in the address book answer locally.  Replies are picked from the
contact's persona, with a few rules on top so that answers actually relate to
what was sent -- especially for picture messages, where a sensible answer
matters more than a witty one.
"""

from __future__ import annotations

import random

from . import people
from .models import Message

# Answers to picture messages, keyed by pictogram.  ``None`` for the picture
# means the reply is text only.
PICTURE_REPLIES: dict[str, list[tuple[str, str | None]]] = {
    "help": [("I am on my way to you now.", "walk"), ("Of course — what do you need?", None)],
    "pain": [("I am sorry. Shall I call the doctor?", "doctor"),
             ("Take it gently, I am coming.", None)],
    "water": [("Coming right up 🥤", "water"), ("I will bring you a glass.", None)],
    "food": [("Dinner is nearly ready.", "food"), ("What would you like to eat?", None)],
    "medicine": [("It is on the shelf by the kettle.", "medicine")],
    "bathroom": [("No problem, take your time.", "yes")],
    "sleep": [("Rest well, we can talk later 🌙", "sleep")],
    "happy": [("That is lovely to hear!", "happy"), ("You have made my day 😊", "love")],
    "sad": [("I am here with you.", "love"), ("Do you want to talk about it?", None)],
    "love": [("Love you too ❤️", "love")],
    "yes": [("Brilliant.", "thanks"), ("Perfect, see you then.", None)],
    "no": [("That is alright, another time.", "yes")],
    "thanks": [("Any time 🙂", "happy")],
    "stop": [("Stopping now. Tell me when you are ready.", "wait")],
    "question": [("Ask away, I am listening.", None)],
    "again": [("Sorry! I said: shall we meet later today?", None)],
    "wait": [("No rush at all.", "wait")],
    "doctor": [("Shall I book the appointment for you?", "phone")],
    "phone": [("Calling you in five minutes.", "phone")],
    "home": [("Glad you are home safe.", "home")],
    "walk": [("Enjoy the fresh air!", "sun")],
    "music": [("Send me the song 🎵", "music")],
    "sun": [("Beautiful here too ☀️", "sun")],
    "rain": [("Pouring here as well. Stay dry!", "rain")],
    "car": [("Text me when you arrive.", "yes")],
    "work": [("Do not work too hard.", None)],
    "book": [("What are you reading?", "book")],
    "ball": [("Who is winning? ⚽", "ball")],
    "family": [("Give everyone my love.", "love")],
    "maybe": [("Let me know when you decide.", "wait")],
}

PERSONA_REPLIES: dict[str, list[tuple[str, str | None]]] = {
    "warm": [
        ("That is so good to hear 💛", None),
        ("Tell me more when you have a minute.", None),
        ("Thinking of you today.", "love"),
        ("You always know how to cheer me up.", "happy"),
    ],
    "practical": [
        ("Understood — I will sort it out.", "yes"),
        ("Noted, thanks for letting me know.", None),
        ("Shall we say tomorrow morning?", "wait"),
        ("All done on my side.", "yes"),
    ],
    "playful": [
        ("Ha! You are trouble 😄", "happy"),
        ("Guess what happened to me today...", None),
        ("Absolutely — count me in!", "yes"),
        ("Sending you a tune to cheer you up 🎵", "music"),
    ],
    "carer": [
        ("Thank you for telling me. How are you feeling now?", None),
        ("I have made a note of that.", "yes"),
        ("Remember to have a drink of water.", "water"),
        ("Call me any time, day or night.", "phone"),
    ],
}

GREETINGS = ("hi", "hello", "hey", "morning", "good morning", "good evening", "hiya")
THANKS = ("thank", "thanks", "cheers", "ta ")
BYES = ("bye", "goodnight", "good night", "see you", "later")


def reply_to(person: people.Person, message: Message) -> Message:
    """Build the answer a contact sends back to ``message``."""
    text, picture = _choose(person, message)
    if person.key == "family":
        # In a group, one of the other members answers.
        sender = random.choice(["priya", "amina"])
    else:
        sender = person.key
    return Message(sender=sender, text=text, picture=picture)


def _choose(person: people.Person, message: Message) -> tuple[str, str | None]:
    if message.picture and message.picture in PICTURE_REPLIES:
        return random.choice(PICTURE_REPLIES[message.picture])

    body = message.text.lower().strip()
    if not body:
        return random.choice(PERSONA_REPLIES[person.persona])
    if any(body.startswith(word) for word in GREETINGS):
        return ("Hello! Good to hear from you 👋", "happy")
    if any(word in body for word in THANKS):
        return ("You are very welcome.", "thanks")
    if any(word in body for word in BYES):
        return ("Talk soon — take care!", "love")
    if "help" in body:
        return ("Tell me what you need and I will help.", "help")
    if "?" in body:
        return random.choice([
            ("Good question — let me think about that.", "question"),
            ("Yes, I think so.", "yes"),
            ("Can I let you know later today?", "wait"),
        ])
    if len(body.split()) <= 2:
        return random.choice([("Got it 👍", "yes"), ("Understood.", None)])
    return random.choice(PERSONA_REPLIES[person.persona])


def typing_delay(message: Message) -> int:
    """Milliseconds before the reply lands, so the chat feels alive."""
    words = len(message.text.split()) + (3 if message.picture else 0)
    return random.randint(900, 1500) + min(2200, words * 90)

