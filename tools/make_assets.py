#!/usr/bin/env python3
"""Draw every picture the app uses and write them to ``assets/``.

Run it with::

    python3 tools/make_assets.py

The generated PNGs are committed, so the app itself never needs this script --
it exists so the artwork can be tweaked (colors, sizes, new pictograms) and
regenerated without any image editor or third-party library.

Glyphs are drawn on a 100x100 design grid and scaled to whatever size is being
rendered, so every picture stays crisp at every size the UI asks for.
"""

from __future__ import annotations

import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, ROOT]

from rasterizer import Raster, mix, rgba  # noqa: E402
from marasender.brand import ORANGE  # noqa: E402
from marasender.colorutil import is_dark  # noqa: E402
from marasender.pictograms import PICTOGRAMS, glyph_ink  # noqa: E402

ASSETS = os.path.join(ROOT, "assets")
WHITE = rgba("#ffffff")


# ---------------------------------------------------------------------------
# Pictogram glyphs.  Each takes the raster, the size, the ink color and the
# tile color (so a glyph can "cut" shapes back out of itself).
# ---------------------------------------------------------------------------
def g_yes(r, S, ink, bg):
    u = S / 100
    r.stroke_path([(24 * u, 52 * u), (43 * u, 72 * u), (78 * u, 28 * u)], 13 * u, ink)


def g_no(r, S, ink, bg):
    u = S / 100
    r.stroke_line(28 * u, 28 * u, 72 * u, 72 * u, 13 * u, ink)
    r.stroke_line(72 * u, 28 * u, 28 * u, 72 * u, 13 * u, ink)


def g_maybe(r, S, ink, bg):
    u = S / 100
    r.stroke_line(28 * u, 50 * u, 72 * u, 50 * u, 11 * u, ink)
    r.fill_poly([(14 * u, 50 * u), (36 * u, 34 * u), (36 * u, 66 * u)], ink)
    r.fill_poly([(86 * u, 50 * u), (64 * u, 34 * u), (64 * u, 66 * u)], ink)


def g_thanks(r, S, ink, bg):  # thumbs up
    u = S / 100
    r.fill_round_rect(36 * u, 44 * u, 76 * u, 84 * u, 10 * u, ink)
    r.stroke_line(48 * u, 48 * u, 56 * u, 18 * u, 16 * u, ink)
    r.fill_round_rect(18 * u, 50 * u, 32 * u, 84 * u, 5 * u, ink)


def g_wait(r, S, ink, bg):  # clock
    u = S / 100
    r.ring(50 * u, 50 * u, 31 * u, 9 * u, ink)
    r.stroke_line(50 * u, 50 * u, 50 * u, 30 * u, 8 * u, ink)
    r.stroke_line(50 * u, 50 * u, 66 * u, 58 * u, 8 * u, ink)


def g_again(r, S, ink, bg):  # circular arrow
    u = S / 100
    r.arc(50 * u, 52 * u, 28 * u, 300, 620, 10 * u, ink)
    r.fill_poly([(78 * u, 22 * u), (78 * u, 52 * u), (50 * u, 38 * u)], ink)


def g_help(r, S, ink, bg):  # raised hand
    u = S / 100
    r.fill_round_rect(32 * u, 46 * u, 76 * u, 86 * u, 12 * u, ink)
    for x, top in ((39, 30), (50, 22), (61, 24), (71, 32)):
        r.stroke_line(x * u, 54 * u, x * u, top * u, 10 * u, ink)
    r.stroke_line(34 * u, 62 * u, 18 * u, 48 * u, 12 * u, ink)


def g_water(r, S, ink, bg):  # droplet
    u = S / 100
    r.fill_circle(50 * u, 62 * u, 25 * u, ink)
    r.fill_poly([(50 * u, 12 * u), (27 * u, 64 * u), (73 * u, 64 * u)], ink)


def g_food(r, S, ink, bg):  # bowl with steam
    u = S / 100
    r.fill_circle(50 * u, 56 * u, 30 * u, ink)
    r.fill_rect(14 * u, 10 * u, 86 * u, 56 * u, bg)
    r.fill_round_rect(12 * u, 50 * u, 88 * u, 60 * u, 5 * u, ink)
    for x in (34, 50, 66):
        r.stroke_path(
            [(x * u, 40 * u), ((x - 7) * u, 31 * u), (x * u, 22 * u), ((x - 7) * u, 13 * u)],
            6 * u, ink,
        )


def g_medicine(r, S, ink, bg):  # capsule, one half solid and one half outlined
    u = S / 100
    r.stroke_line(30 * u, 70 * u, 70 * u, 30 * u, 32 * u, ink)
    r.stroke_line(53 * u, 47 * u, 66 * u, 34 * u, 22 * u, bg)
    r.stroke_line(39 * u, 39 * u, 61 * u, 61 * u, 5 * u, bg, caps=False)


def g_bathroom(r, S, ink, bg):  # shower
    u = S / 100
    r.fill_round_rect(26 * u, 22 * u, 74 * u, 34 * u, 6 * u, ink)
    r.stroke_line(50 * u, 22 * u, 50 * u, 12 * u, 8 * u, ink)
    for i, x in enumerate((32, 44, 56, 68)):
        y = 46 + (i % 2) * 8
        r.stroke_line(x * u, y * u, (x - 4) * u, (y + 20) * u, 7 * u, ink)


def g_pain(r, S, ink, bg):  # sticking plaster
    u = S / 100
    r.stroke_line(26 * u, 74 * u, 74 * u, 26 * u, 26 * u, ink)
    for dx, dy in ((-8, -8), (8, 8), (-8, 8), (8, -8)):
        r.fill_circle((50 + dx) * u, (50 + dy) * u, 4 * u, bg)


def g_sleep(r, S, ink, bg):  # crescent moon
    u = S / 100
    r.fill_circle(52 * u, 52 * u, 30 * u, ink)
    r.fill_circle(68 * u, 36 * u, 27 * u, bg)
    r.star(26 * u, 26 * u, 9 * u, 4, 0.35, ink)
    r.star(76 * u, 76 * u, 6 * u, 4, 0.35, ink)


def g_stop(r, S, ink, bg):  # no-entry sign
    u = S / 100
    pts = [
        (
            (50 + 34 * math.cos(math.radians(a))) * u,
            (50 + 34 * math.sin(math.radians(a))) * u,
        )
        for a in range(22, 382, 45)
    ]
    r.fill_poly(pts, ink)
    r.fill_round_rect(28 * u, 43 * u, 72 * u, 57 * u, 5 * u, bg)


def _face(r, S, ink, smile: bool):
    u = S / 100
    r.ring(50 * u, 50 * u, 31 * u, 8 * u, ink)
    r.fill_circle(39 * u, 42 * u, 5.5 * u, ink)
    r.fill_circle(61 * u, 42 * u, 5.5 * u, ink)
    if smile:
        r.arc(50 * u, 54 * u, 18 * u, 25, 155, 8 * u, ink)
    else:
        r.arc(50 * u, 78 * u, 18 * u, 205, 335, 8 * u, ink)


def g_happy(r, S, ink, bg):
    _face(r, S, ink, True)


def g_sad(r, S, ink, bg):
    _face(r, S, ink, False)


def g_love(r, S, ink, bg):  # heart
    u = S / 100
    r.fill_circle(37 * u, 40 * u, 19 * u, ink)
    r.fill_circle(63 * u, 40 * u, 19 * u, ink)
    r.fill_poly([(18 * u, 44 * u), (82 * u, 44 * u), (50 * u, 84 * u)], ink)


def g_question(r, S, ink, bg):
    u = S / 100
    r.arc(50 * u, 38 * u, 16 * u, 180, 400, 10 * u, ink)
    r.stroke_line(60 * u, 50 * u, 50 * u, 64 * u, 10 * u, ink)
    r.fill_circle(50 * u, 80 * u, 7 * u, ink)


def g_home(r, S, ink, bg):
    u = S / 100
    r.fill_poly([(50 * u, 14 * u), (90 * u, 50 * u), (10 * u, 50 * u)], ink)
    r.fill_rect(22 * u, 48 * u, 78 * u, 86 * u, ink)
    r.fill_round_rect(41 * u, 62 * u, 59 * u, 86 * u, 3 * u, bg)


def _person(r, u, cx, cy, head, body_w, body_h, color):
    r.fill_circle(cx * u, cy * u, head * u, color)
    r.fill_round_rect(
        (cx - body_w / 2) * u,
        (cy + head * 0.6) * u,
        (cx + body_w / 2) * u,
        (cy + head * 0.6 + body_h) * u,
        body_w / 2 * u,
        color,
    )


def g_family(r, S, ink, bg):
    u = S / 100
    _person(r, u, 26, 30, 11, 26, 32, ink)
    _person(r, u, 74, 30, 11, 26, 32, ink)
    _person(r, u, 50, 52, 13, 30, 34, bg)      # halo keeps the child readable
    _person(r, u, 50, 54, 10, 24, 28, ink)


def g_doctor(r, S, ink, bg):  # medical cross
    u = S / 100
    r.fill_round_rect(40 * u, 16 * u, 60 * u, 84 * u, 5 * u, ink)
    r.fill_round_rect(16 * u, 40 * u, 84 * u, 60 * u, 5 * u, ink)


def g_work(r, S, ink, bg):  # briefcase
    u = S / 100
    r.stroke_path(
        [(38 * u, 40 * u), (38 * u, 26 * u), (62 * u, 26 * u), (62 * u, 40 * u)], 8 * u, ink
    )
    r.fill_round_rect(14 * u, 36 * u, 86 * u, 82 * u, 8 * u, ink)
    r.fill_rect(14 * u, 54 * u, 86 * u, 61 * u, bg)


def g_car(r, S, ink, bg):
    u = S / 100
    r.fill_poly([(30 * u, 52 * u), (40 * u, 30 * u), (66 * u, 30 * u), (76 * u, 52 * u)], ink)
    r.fill_round_rect(12 * u, 48 * u, 88 * u, 70 * u, 9 * u, ink)
    for x in (30, 70):
        r.fill_circle(x * u, 72 * u, 11 * u, ink)
        r.fill_circle(x * u, 72 * u, 4.5 * u, bg)


def g_walk(r, S, ink, bg):
    u = S / 100
    r.fill_circle(56 * u, 20 * u, 11 * u, ink)
    r.stroke_line(56 * u, 32 * u, 46 * u, 56 * u, 10 * u, ink)
    r.stroke_path([(46 * u, 56 * u), (58 * u, 70 * u), (56 * u, 88 * u)], 9 * u, ink)
    r.stroke_path([(46 * u, 56 * u), (32 * u, 70 * u), (22 * u, 82 * u)], 9 * u, ink)
    r.stroke_line(52 * u, 40 * u, 70 * u, 50 * u, 8 * u, ink)
    r.stroke_line(52 * u, 40 * u, 34 * u, 44 * u, 8 * u, ink)


def g_phone(r, S, ink, bg):  # handset
    u = S / 100
    r.stroke_line(24 * u, 36 * u, 38 * u, 22 * u, 20 * u, ink)
    r.stroke_line(62 * u, 78 * u, 76 * u, 64 * u, 20 * u, ink)
    r.stroke_line(33 * u, 42 * u, 58 * u, 68 * u, 13 * u, ink)


def g_music(r, S, ink, bg):
    u = S / 100
    r.stroke_line(62 * u, 24 * u, 62 * u, 66 * u, 8 * u, ink)
    r.fill_circle(52 * u, 68 * u, 14 * u, ink)
    r.fill_poly([(62 * u, 20 * u), (84 * u, 30 * u), (84 * u, 44 * u), (62 * u, 34 * u)], ink)


def g_sun(r, S, ink, bg):
    u = S / 100
    r.fill_circle(50 * u, 50 * u, 22 * u, ink)
    for a in range(0, 360, 45):
        rad = math.radians(a)
        r.stroke_line(
            (50 + 30 * math.cos(rad)) * u,
            (50 + 30 * math.sin(rad)) * u,
            (50 + 43 * math.cos(rad)) * u,
            (50 + 43 * math.sin(rad)) * u,
            8 * u,
            ink,
        )


def g_rain(r, S, ink, bg):
    u = S / 100
    r.fill_circle(36 * u, 42 * u, 16 * u, ink)
    r.fill_circle(56 * u, 36 * u, 20 * u, ink)
    r.fill_circle(72 * u, 48 * u, 13 * u, ink)
    r.fill_round_rect(22 * u, 44 * u, 80 * u, 62 * u, 8 * u, ink)
    for x in (36, 52, 68):
        r.stroke_line(x * u, 70 * u, (x - 5) * u, 86 * u, 7 * u, ink)


def g_book(r, S, ink, bg):
    u = S / 100
    r.fill_poly([(12 * u, 26 * u), (47 * u, 36 * u), (47 * u, 84 * u), (12 * u, 74 * u)], ink)
    r.fill_poly([(88 * u, 26 * u), (53 * u, 36 * u), (53 * u, 84 * u), (88 * u, 74 * u)], ink)


def g_ball(r, S, ink, bg):
    u = S / 100
    r.ring(50 * u, 50 * u, 31 * u, 8 * u, ink)
    r.fill_poly([
        ((50 + 16 * math.cos(math.radians(a))) * u,
         (50 + 16 * math.sin(math.radians(a))) * u)
        for a in range(-90, 270, 72)
    ], ink)
    for a in range(-90, 270, 72):
        rad = math.radians(a)
        r.stroke_line(
            (50 + 15 * math.cos(rad)) * u,
            (50 + 15 * math.sin(rad)) * u,
            (50 + 27 * math.cos(rad)) * u,
            (50 + 27 * math.sin(rad)) * u,
            7 * u,
            ink,
        )


GLYPHS = {
    "yes": g_yes, "no": g_no, "maybe": g_maybe, "thanks": g_thanks, "wait": g_wait,
    "again": g_again, "help": g_help, "water": g_water, "food": g_food,
    "medicine": g_medicine, "bathroom": g_bathroom, "pain": g_pain, "sleep": g_sleep,
    "stop": g_stop, "happy": g_happy, "sad": g_sad, "love": g_love,
    "question": g_question, "home": g_home, "family": g_family, "doctor": g_doctor,
    "work": g_work, "car": g_car, "walk": g_walk, "phone": g_phone, "music": g_music,
    "sun": g_sun, "rain": g_rain, "book": g_book, "ball": g_ball,
}


# ---------------------------------------------------------------------------
# Avatars
# ---------------------------------------------------------------------------
def draw_badge(r, S, shape: str, color, ink):
    """The colour-free identifier stamped on the corner of every avatar."""
    u = S / 100
    cx, cy, rad = 79 * u, 79 * u, 19 * u
    r.fill_circle(cx, cy, rad, color)
    r.ring(cx, cy, rad, 3 * u, rgba("#ffffff", 220))
    s = rad * 0.62
    if shape == "circle":
        r.fill_circle(cx, cy, s * 0.85, ink)
    elif shape == "square":
        r.fill_rect(cx - s * 0.8, cy - s * 0.8, cx + s * 0.8, cy + s * 0.8, ink)
    elif shape == "triangle":
        r.fill_poly([(cx, cy - s), (cx + s, cy + s * 0.8), (cx - s, cy + s * 0.8)], ink)
    elif shape == "star":
        r.star(cx, cy, s * 1.15, 5, 0.45, ink)
    elif shape == "diamond":
        r.fill_poly([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], ink)
    elif shape == "heart":
        r.fill_circle(cx - s * 0.42, cy - s * 0.25, s * 0.55, ink)
        r.fill_circle(cx + s * 0.42, cy - s * 0.25, s * 0.55, ink)
        r.fill_poly([(cx - s * 0.95, cy - s * 0.1),
                     (cx + s * 0.95, cy - s * 0.1), (cx, cy + s)], ink)
    elif shape == "hexagon":
        r.fill_poly([
            (cx + s * math.cos(math.radians(a)), cy + s * math.sin(math.radians(a)))
            for a in range(0, 360, 60)
        ], ink)
    elif shape == "plus":
        r.fill_rect(cx - s * 0.3, cy - s, cx + s * 0.3, cy + s, ink)
        r.fill_rect(cx - s, cy - s * 0.3, cx + s, cy + s * 0.3, ink)
    elif shape == "group":
        r.fill_circle(cx - s * 0.45, cy - s * 0.2, s * 0.45, ink)
        r.fill_circle(cx + s * 0.45, cy - s * 0.2, s * 0.45, ink)
        r.fill_round_rect(cx - s, cy + s * 0.15, cx + s, cy + s, s * 0.4, ink)


SKIN_TONES = (
    "#f0d0b4", "#e8bd97", "#d9a273", "#c1834f", "#a3663a",
    "#7d4b26", "#f5dcc4", "#b5754a", "#8a5a33",
)


def draw_hair(r, S, style: int, hair, behind: bool) -> None:
    """Hair is drawn in two passes so long styles sit behind the head."""
    u = S / 100
    if behind:
        if style == 1:                                    # long hair
            r.fill_round_rect(27 * u, 24 * u, 73 * u, 74 * u, 23 * u, hair)
        elif style == 3:                                  # bun
            r.fill_circle(50 * u, 16 * u, 11 * u, hair)
        elif style == 5:                                  # curls
            for dx in (-17, 0, 17):
                r.fill_circle((50 + dx) * u, 30 * u, 13 * u, hair)
        elif style == 7:                                  # beard
            r.fill_circle(50 * u, 50 * u, 24 * u, hair)
        return
    if style in (1, 3):
        r.arc(50 * u, 45 * u, 21 * u, 190, 350, 12 * u, hair)
    elif style == 2:
        r.arc(50 * u, 45 * u, 21 * u, 195, 345, 11 * u, hair)
    elif style == 4:                                      # cap with a brim
        r.arc(50 * u, 44 * u, 22 * u, 195, 345, 14 * u, hair)
        r.fill_round_rect(22 * u, 30 * u, 60 * u, 37 * u, 4 * u, hair)
    elif style == 5:
        r.arc(50 * u, 45 * u, 21 * u, 195, 345, 10 * u, hair)
    elif style == 6:                                      # side parting
        r.fill_poly([(29 * u, 44 * u), (36 * u, 25 * u), (71 * u, 27 * u), (70 * u, 38 * u)], hair)
    elif style == 7:
        r.arc(50 * u, 45 * u, 21 * u, 195, 345, 11 * u, hair)


def draw_face(r, S, ink) -> None:
    u = S / 100
    r.fill_circle(43 * u, 48 * u, 2.6 * u, ink)
    r.fill_circle(57 * u, 48 * u, 2.6 * u, ink)
    r.arc(50 * u, 52 * u, 8 * u, 30, 150, 2.4 * u, ink)


def draw_avatar(size: int, person_color: str, style: int, badge: str) -> Raster:
    """A friendly illustrated portrait: skin tone and hair vary per person, the
    background carries the contact colour and the badge repeats the identity
    as a shape."""
    u = size / 100
    r = Raster(size, size, ss=3)
    # Half the brand colours are pale, so the backdrop is deepened for those
    # instead of lightened -- otherwise the face would vanish into it.
    pale = not is_dark(person_color)
    top = mix(person_color, "#000000", 0.10) if pale else mix(person_color, "#ffffff", 0.34)
    bottom = mix(person_color, "#000000", 0.34 if pale else 0.10)
    r.fill_rect(0, 0, size, size / 2, rgba(top))
    r.fill_rect(0, size / 2, size, size, rgba(bottom))
    skin = rgba(SKIN_TONES[style % len(SKIN_TONES)])
    hair = rgba(mix(person_color, "#1a1108", 0.72 if pale else 0.62))
    shirt = rgba(mix(person_color, "#000000", 0.55) if pale
                 else mix(person_color, "#ffffff", 0.72))
    line = rgba("#3a2a1e", 210)

    if style == 8:  # the group avatar shows two people
        r.fill_circle(30 * u, 100 * u, 28 * u, shirt)
        r.fill_circle(70 * u, 96 * u, 32 * u,
                      rgba(mix(person_color, "#000000" if pale else "#ffffff", 0.4)))
        r.fill_circle(30 * u, 46 * u, 15 * u, rgba(SKIN_TONES[2]))
        r.fill_circle(70 * u, 50 * u, 18 * u, rgba(SKIN_TONES[5]))
        r.arc(30 * u, 46 * u, 15 * u, 195, 345, 9 * u, hair)
        r.arc(70 * u, 50 * u, 18 * u, 190, 350, 10 * u, hair)
    else:
        r.fill_circle(50 * u, 106 * u, 36 * u, shirt)      # shoulders
        r.fill_circle(50 * u, 78 * u, 12 * u, skin)        # neck
        draw_hair(r, size, style, hair, behind=True)
        r.fill_circle(31 * u, 50 * u, 4.5 * u, skin)       # ears
        r.fill_circle(69 * u, 50 * u, 4.5 * u, skin)
        r.fill_ellipse(50 * u, 48 * u, 20 * u, 22 * u, skin)
        draw_face(r, size, line)
        draw_hair(r, size, style, hair, behind=False)

    r.clip_circle(size / 2, size / 2, size / 2 - 0.5)
    draw_badge(r, size, badge, rgba(mix(person_color, "#000000", 0.45)), rgba("#ffffff"))
    return r


# ---------------------------------------------------------------------------
# Interface icons
# ---------------------------------------------------------------------------
def i_send(r, S, ink):
    u = S / 100
    r.fill_poly([(12 * u, 52 * u), (88 * u, 18 * u), (60 * u, 86 * u), (48 * u, 60 * u)], ink)


def i_attach(r, S, ink):  # paperclip
    u = S / 100
    r.stroke_line(64 * u, 22 * u, 64 * u, 68 * u, 9 * u, ink)
    r.arc(46 * u, 68 * u, 18 * u, 0, 180, 9 * u, ink)
    r.stroke_line(28 * u, 68 * u, 28 * u, 40 * u, 9 * u, ink)
    r.arc(42 * u, 40 * u, 14 * u, 180, 360, 9 * u, ink)
    r.stroke_line(56 * u, 40 * u, 56 * u, 62 * u, 9 * u, ink)


def i_search(r, S, ink):
    u = S / 100
    r.ring(44 * u, 44 * u, 23 * u, 9 * u, ink)
    r.stroke_line(60 * u, 60 * u, 84 * u, 84 * u, 11 * u, ink)


def i_settings(r, S, ink):
    u = S / 100
    for a in range(0, 360, 45):
        rad = math.radians(a)
        r.stroke_line(
            (50 + 20 * math.cos(rad)) * u, (50 + 20 * math.sin(rad)) * u,
            (50 + 38 * math.cos(rad)) * u, (50 + 38 * math.sin(rad)) * u, 20 * u, ink,
        )
    r.fill_circle(50 * u, 50 * u, 30 * u, ink)
    r.erase_circle(50 * u, 50 * u, 12 * u)


def i_speak(r, S, ink):
    u = S / 100
    r.fill_poly([
        (14 * u, 40 * u), (32 * u, 40 * u), (50 * u, 20 * u),
        (50 * u, 80 * u), (32 * u, 60 * u), (14 * u, 60 * u),
    ], ink)
    r.arc(52 * u, 50 * u, 16 * u, -55, 55, 7 * u, ink)
    r.arc(52 * u, 50 * u, 30 * u, -55, 55, 7 * u, ink)


def i_contrast(r, S, ink):  # half-filled circle: the light / dark switch
    u = S / 100
    r.fill_circle(50 * u, 50 * u, 30 * u, ink)
    r.erase_rect(0, 0, 50 * u, S)
    r.ring(50 * u, 50 * u, 30 * u, 8 * u, ink)


def _letter_a(r, u, cx, cy, h, w, ink):
    r.stroke_path([(cx - w, cy + h), (cx, cy - h), (cx + w, cy + h)], w * 0.45, ink)
    r.stroke_line(cx - w * 0.55, cy + h * 0.25, cx + w * 0.55, cy + h * 0.25, w * 0.4, ink)


def i_text_bigger(r, S, ink):
    u = S / 100
    _letter_a(r, u, 34 * u, 52 * u, 30 * u, 22 * u, ink)
    r.stroke_line(78 * u, 78 * u, 78 * u, 26 * u, 9 * u, ink)
    r.fill_poly([(78 * u, 16 * u), (92 * u, 36 * u), (64 * u, 36 * u)], ink)


def i_text_smaller(r, S, ink):
    u = S / 100
    _letter_a(r, u, 34 * u, 56 * u, 22 * u, 17 * u, ink)
    r.stroke_line(78 * u, 22 * u, 78 * u, 74 * u, 9 * u, ink)
    r.fill_poly([(78 * u, 84 * u), (92 * u, 64 * u), (64 * u, 64 * u)], ink)


def i_board(r, S, ink):
    u = S / 100
    for x0, y0 in ((12, 12), (54, 12), (12, 54), (54, 54)):
        r.fill_round_rect(x0 * u, y0 * u, (x0 + 34) * u, (y0 + 34) * u, 7 * u, ink)


def i_plus(r, S, ink):
    u = S / 100
    r.fill_round_rect(42 * u, 16 * u, 58 * u, 84 * u, 6 * u, ink)
    r.fill_round_rect(16 * u, 42 * u, 84 * u, 58 * u, 6 * u, ink)


def i_back(r, S, ink):
    u = S / 100
    r.stroke_path([(62 * u, 20 * u), (32 * u, 50 * u), (62 * u, 80 * u)], 12 * u, ink)


def i_close(r, S, ink):
    u = S / 100
    r.stroke_line(26 * u, 26 * u, 74 * u, 74 * u, 12 * u, ink)
    r.stroke_line(74 * u, 26 * u, 26 * u, 74 * u, 12 * u, ink)


def i_info(r, S, ink):
    u = S / 100
    r.ring(50 * u, 50 * u, 33 * u, 9 * u, ink)
    r.fill_circle(50 * u, 30 * u, 6 * u, ink)
    r.fill_round_rect(44 * u, 44 * u, 56 * u, 74 * u, 5 * u, ink)


def i_tick_sent(r, S, ink):
    u = S / 100
    r.stroke_path([(16 * u, 54 * u), (38 * u, 76 * u), (84 * u, 24 * u)], 13 * u, ink)


def i_tick_read(r, S, ink):
    u = S / 100
    r.stroke_path([(6 * u, 54 * u), (26 * u, 74 * u), (62 * u, 28 * u)], 12 * u, ink)
    r.stroke_path([(38 * u, 54 * u), (56 * u, 74 * u), (94 * u, 26 * u)], 12 * u, ink)


def i_call(r, S, ink):
    g_phone(r, S, ink, None)


def i_video(r, S, ink):
    u = S / 100
    r.fill_round_rect(10 * u, 30 * u, 64 * u, 74 * u, 9 * u, ink)
    r.fill_poly([(68 * u, 44 * u), (90 * u, 28 * u), (90 * u, 76 * u), (68 * u, 60 * u)], ink)


def i_emoji(r, S, ink):
    _face(r, S, ink, True)


ICONS = {
    "send": i_send, "attach": i_attach, "search": i_search, "settings": i_settings,
    "speak": i_speak, "contrast": i_contrast, "text_bigger": i_text_bigger,
    "text_smaller": i_text_smaller, "board": i_board, "plus": i_plus, "back": i_back,
    "close": i_close, "info": i_info, "tick_sent": i_tick_sent,
    "tick_read": i_tick_read, "call": i_call, "video": i_video, "emoji": i_emoji,
}

# ---------------------------------------------------------------------------
# The wordmark.
#
# The app name is set in Bauhaus 93 when the machine has it (it ships with
# Microsoft Office).  Everywhere else these drawn letters stand in: geometric
# shapes in the spirit of that face -- circular bowls, straight stems, one
# heavy weight, flat terminals -- so the app is recognisable on any machine.
#
# Letters are drawn on a grid where the cap height is 100 units, the
# x-height 74, and the stroke 22.
# ---------------------------------------------------------------------------
CAP, XH, STROKE = 100.0, 74.0, 22.0
BOWL = XH / 2                      # outer radius of a lowercase bowl
RING = STROKE                      # ring thickness


def _stem(r, u, x, y0, y1, ink, width=STROKE):
    r.fill_rect(x * u, y0 * u, (x + width) * u, y1 * u, ink)


def w_M(r, u, x, ink):
    _stem(r, u, x, 0, CAP, ink)
    _stem(r, u, x + 78, 0, CAP, ink)
    r.stroke_line((x + 11) * u, 0, (x + 50) * u, 66 * u, STROKE * u, ink, caps=False)
    r.stroke_line((x + 50) * u, 66 * u, (x + 89) * u, 0, STROKE * u, ink, caps=False)
    r.fill_circle((x + 50) * u, 66 * u, STROKE * u / 2, ink)   # fill the vertex
    return 100


def w_S(r, u, x, ink):
    # Two overlapping bowls, each sweeping about three quarters of a circle:
    # the top one open at its lower right, the bottom one at its upper left.
    cx = x + 37
    r.arc(cx * u, 30 * u, 27 * u, 315, 45, RING * u, ink)
    r.arc(cx * u, 70 * u, 27 * u, 225, 495, RING * u, ink)
    return 74


def w_a(r, u, x, ink):
    r.ring((x + BOWL) * u, (CAP - BOWL) * u, BOWL * u - RING * u / 2, RING * u, ink)
    _stem(r, u, x + XH - STROKE, CAP - XH, CAP, ink)
    return 74


def w_d(r, u, x, ink):
    r.ring((x + BOWL) * u, (CAP - BOWL) * u, BOWL * u - RING * u / 2, RING * u, ink)
    _stem(r, u, x + XH - STROKE, 0, CAP, ink)
    return 74


def w_e(r, u, x, ink):
    cx, cy = x + BOWL, CAP - BOWL
    radius = BOWL - RING / 2
    r.arc(cx * u, cy * u, radius * u, 55, 360, RING * u, ink)
    r.fill_rect((cx - radius - RING / 2) * u, (cy - RING / 2) * u,
                (cx + radius + RING / 2) * u, (cy + RING / 2) * u, ink)
    return 74


def w_n(r, u, x, ink):
    _stem(r, u, x, CAP - XH, CAP, ink)
    _stem(r, u, x + XH - STROKE, CAP - XH + BOWL - RING / 2, CAP, ink)
    r.arc((x + BOWL) * u, (CAP - XH + BOWL - RING / 2) * u,
          (BOWL - RING / 2) * u, 180, 360, RING * u, ink)
    return 74


def w_r(r, u, x, ink):
    _stem(r, u, x, CAP - XH, CAP, ink)
    r.arc((x + 28) * u, (CAP - XH + 28) * u, 28 * u - RING * u / 2, 180, 275, RING * u, ink)
    return 46


WORDMARK = "MaraSender"
WORDMARK_GLYPHS = {
    "M": w_M, "S": w_S, "a": w_a, "d": w_d, "e": w_e, "n": w_n, "r": w_r,
}
LETTER_GAP = 9
# Round letters are given a little less room on each side so the spacing looks
# even -- a circle beside a straight stem always reads as a wider gap.
SIDE_BEARING = {"a": -4, "d": -4, "e": -4, "n": -2, "S": -3, "r": 0, "M": 0}
# A couple of pairs need pulling together by hand: the arm of "r" hangs over
# the letter that follows it, leaving a hole at the baseline.
KERN = {("r", "a"): -9, ("a", "S"): -3}
WORDMARK_HEIGHTS = (26, 32, 40, 52, 64)


ADVANCE = {"M": 100, "S": 74, "a": 74, "d": 74, "e": 74, "n": 74, "r": 46}


def wordmark_width_units() -> float:
    total = 0.0
    for index, letter in enumerate(WORDMARK):
        total += ADVANCE[letter] + SIDE_BEARING[letter] * 2
        if index < len(WORDMARK) - 1:
            total += LETTER_GAP + KERN.get((letter, WORDMARK[index + 1]), 0)
    return total


def draw_wordmark(cap_height: int, color: str) -> Raster:
    u = cap_height / CAP
    pad = 3
    width = round(wordmark_width_units() * u) + pad * 2
    r = Raster(width, cap_height + pad * 2, ss=3)
    ink = rgba(color)
    x = pad / u
    for index, letter in enumerate(WORDMARK):
        x += SIDE_BEARING[letter]
        advance = WORDMARK_GLYPHS[letter](r, u, x, ink)
        x += advance + SIDE_BEARING[letter] + LETTER_GAP
        if index < len(WORDMARK) - 1:
            x += KERN.get((letter, WORDMARK[index + 1]), 0)
    return r


PICTOGRAM_SIZES = (128, 64)
AVATAR_SIZES = (96, 44)
ICON_SIZES = (20, 26, 34)
INKS = {"light": "#ffffff", "dark": "#1b2430"}
# The "read" ticks are blue, the way people expect them to be.
EXTRA_INKS = {"tick_sent": {}, "tick_read": {"read": "#1d6ff2", "read_bright": "#57d1ff"}}


def main() -> None:
    started = time.time()
    for folder in ("pictograms", "avatars", "icons"):
        os.makedirs(os.path.join(ASSETS, folder), exist_ok=True)

    count = 0
    for pic in PICTOGRAMS:
        glyph = GLYPHS[pic.key]
        for size in PICTOGRAM_SIZES:
            r = Raster(size, size, ss=3)
            tile = rgba(pic.color)
            r.fill_round_rect(0, 0, size, size, size * 0.22, tile)
            r.fill_round_rect(0, 0, size, size * 0.5, size * 0.22,
                              rgba(mix(pic.color, "#ffffff", 0.12)))
            r.fill_round_rect(0, size * 0.28, size, size, size * 0.22, tile)
            glyph(r, size, rgba(glyph_ink(pic)), tile)
            r.save(os.path.join(ASSETS, "pictograms", f"{pic.key}_{size}.png"))
            count += 1

    from marasender.people import CONTACTS, ME

    for person in (ME, *CONTACTS):
        for size in AVATAR_SIZES:
            draw_avatar(size, person.color, person.style, person.badge).save(
                os.path.join(ASSETS, "avatars", f"{person.key}_{size}.png")
            )
            count += 1

    for name, draw in ICONS.items():
        inks = dict(INKS, **EXTRA_INKS.get(name, {}))
        for ink_name, ink_hex in inks.items():
            for size in ICON_SIZES:
                r = Raster(size, size, ss=4)
                draw(r, size, rgba(ink_hex))
                r.save(os.path.join(ASSETS, "icons", f"{name}_{ink_name}_{size}.png"))
                count += 1

    os.makedirs(os.path.join(ASSETS, "wordmark"), exist_ok=True)
    for height in WORDMARK_HEIGHTS:
        raster = draw_wordmark(height, ORANGE)
        # The wordmark is drawn a few units above the baseline of the grid, so
        # it is nudged into place by the padding built into draw_wordmark().
        raster.save(os.path.join(ASSETS, "wordmark", f"wordmark_{height}.png"))
        count += 1

    print(f"wrote {count} images to {ASSETS} in {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()
