"""Tests for Marasender.

Run them with::

    python3 -m unittest discover -s tests -v

The tests that need a screen (anything touching Tk) skip themselves when there
is no display, so the rest still run on a headless machine.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from marasender import APP_NAME, bots, brand, models, people, theme  # noqa: E402
from marasender.assets import (  # noqa: E402
    ASSET_ROOT, AVATAR_SIZES, ICON_SIZES, PICTOGRAM_SIZES, WORDMARK_HEIGHTS,
)
from marasender.pictograms import (  # noqa: E402
    BY_KEY, CATEGORIES, PICTOGRAMS, glyph_ink, in_category,
)
from marasender.colorutil import text_ink  # noqa: E402
from marasender.textutil import elide  # noqa: E402

ICON_NAMES = (
    "send", "attach", "search", "settings", "speak", "contrast", "text_bigger",
    "text_smaller", "board", "plus", "back", "close", "info", "tick_sent",
    "tick_read", "call", "video", "emoji",
)


class TestPictures(unittest.TestCase):
    """Every picture the app asks for has to exist on disk."""

    def test_pictogram_files_exist(self):
        for pictogram in PICTOGRAMS:
            for size in PICTOGRAM_SIZES:
                path = os.path.join(ASSET_ROOT, "pictograms", f"{pictogram.key}_{size}.png")
                self.assertTrue(os.path.exists(path), f"missing {path}")

    def test_avatar_files_exist(self):
        for person in (people.ME, *people.CONTACTS):
            for size in AVATAR_SIZES:
                path = os.path.join(ASSET_ROOT, "avatars", f"{person.key}_{size}.png")
                self.assertTrue(os.path.exists(path), f"missing {path}")

    def test_icon_files_exist(self):
        for name in ICON_NAMES:
            for ink in ("light", "dark"):
                for size in ICON_SIZES:
                    path = os.path.join(ASSET_ROOT, "icons", f"{name}_{ink}_{size}.png")
                    self.assertTrue(os.path.exists(path), f"missing {path}")

    def test_wordmark_files_exist(self):
        for height in WORDMARK_HEIGHTS:
            path = os.path.join(ASSET_ROOT, "wordmark", f"wordmark_{height}.png")
            self.assertTrue(os.path.exists(path), f"missing {path}")

    def test_files_are_pngs(self):
        path = os.path.join(ASSET_ROOT, "pictograms", "yes_128.png")
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n")

    def test_there_are_plenty_of_pictures(self):
        # The picture board is only useful with a real vocabulary behind it.
        self.assertGreaterEqual(len(PICTOGRAMS), 24)

    def test_every_pictogram_is_reachable_from_a_category(self):
        reachable = {p.key for name in CATEGORIES for p in in_category(name)}
        self.assertEqual(reachable, {p.key for p in PICTOGRAMS})

    def test_pictograms_have_words_and_sentences(self):
        for pictogram in PICTOGRAMS:
            self.assertTrue(pictogram.label.strip(), pictogram.key)
            self.assertTrue(pictogram.message.strip(), pictogram.key)


class TestPeople(unittest.TestCase):
    def test_contacts_are_distinguishable_without_colour(self):
        badges = [person.badge for person in people.CONTACTS]
        self.assertEqual(len(badges), len(set(badges)), "two contacts share a badge shape")

    def test_contacts_have_distinct_colours(self):
        colors = [person.color for person in people.CONTACTS]
        self.assertEqual(len(colors), len(set(colors)))

    def test_every_badge_has_a_word(self):
        for person in (people.ME, *people.CONTACTS):
            self.assertIn(person.badge, people.BADGE_NAMES)


class TestColours(unittest.TestCase):
    """Colour is the whole point of the app, so it has to stay readable."""

    def test_palette_text_meets_wcag_aa(self):
        for palette in theme.PALETTES:
            for foreground, background in (
                (palette.text, palette.panel),
                (palette.text, palette.canvas),
                (palette.text_soft, palette.panel),
                (palette.bar_text, palette.bar),
                (palette.accent_text, palette.accent),
                (palette.mine_text, palette.mine_bg),
            ):
                ratio = theme.contrast_ratio(foreground, background)
                self.assertGreaterEqual(ratio, 4.5, f"{palette.key}: {foreground} on {background}")

    def test_contact_bubbles_are_readable(self):
        for palette in theme.PALETTES:
            active = theme.Theme.__new__(theme.Theme)
            active.palette = palette
            for person in people.CONTACTS:
                background, _outline, ink = active.contact_bubble(person.color)
                ratio = theme.contrast_ratio(ink, background)
                self.assertGreaterEqual(
                    ratio, 4.5, f"{palette.key}/{person.key}: {ink} on {background}"
                )

    def test_contact_names_are_readable_on_the_panel(self):
        for palette in theme.PALETTES:
            active = theme.Theme.__new__(theme.Theme)
            active.palette = palette
            for person in people.CONTACTS:
                ink = active.contact_ink(person.color)
                ratio = theme.contrast_ratio(ink, palette.panel)
                self.assertGreaterEqual(ratio, 4.5, f"{palette.key}/{person.key}")

    def test_pictogram_glyphs_stand_out_from_their_tile(self):
        for pictogram in PICTOGRAMS:
            ratio = theme.contrast_ratio(glyph_ink(pictogram), pictogram.color)
            self.assertGreaterEqual(ratio, 3.0, pictogram.key)

    def test_readable_gives_up_gracefully(self):
        self.assertEqual(theme.readable("#000000", "#000000", 21.0), "#ffffff")


class TestBrandColours(unittest.TestCase):
    """Everything visible is one of the six brand colours, or a deeper one."""

    def family(self):
        return set(brand.BRAND) | set(brand.DEEP)

    def test_contacts_come_from_the_brand_palette(self):
        for person in (people.ME, *people.CONTACTS):
            self.assertIn(person.color, self.family(), person.key)

    def test_picture_tiles_come_from_the_brand_palette(self):
        for pictogram in PICTOGRAMS:
            self.assertIn(pictogram.color, self.family(), pictogram.key)

    def test_tiles_on_screen_together_never_share_a_colour(self):
        for name in CATEGORIES:
            colors = [p.color for p in in_category(name)]
            self.assertEqual(len(colors), len(set(colors)), f"repeated colour in {name}")

    def test_the_wordmark_is_always_the_brand_orange(self):
        # The drawn fallback is painted in one fixed colour, so no palette may
        # ask for a different one.
        for palette in theme.PALETTES:
            self.assertEqual(palette.wordmark, brand.ORANGE, palette.key)

    def test_the_name_stands_out_on_the_app_bar(self):
        for palette in theme.PALETTES:
            ratio = theme.contrast_ratio(palette.wordmark, palette.bar)
            self.assertGreaterEqual(ratio, 4.5, palette.key)

    def test_each_palette_leads_with_a_brand_colour(self):
        for palette in theme.PALETTES:
            self.assertIn(palette.accent, self.family(), palette.key)

    def test_ink_is_chosen_by_contrast_not_by_guesswork(self):
        for color in brand.BRAND + brand.DEEP:
            ink = text_ink(color)
            other = "#ffffff" if ink != "#ffffff" else "#12181f"
            self.assertGreaterEqual(
                theme.contrast_ratio(ink, color), theme.contrast_ratio(other, color), color
            )
            self.assertGreaterEqual(theme.contrast_ratio(ink, color), 4.5, color)


class TestStore(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, "chats.json")

    def tearDown(self):
        self.folder.cleanup()

    def test_seeds_then_reloads(self):
        store = models.Store(self.path)
        self.assertEqual(set(store.chats), {p.key for p in people.CONTACTS})
        store.chats["luca"].add(models.Message(sender="me", text="hello there"))
        store.save()

        again = models.Store(self.path)
        self.assertEqual(again.chats["luca"].last().text, "hello there")

    def test_unread_counting_and_mark_read(self):
        store = models.Store(self.path)
        chat = store.chats["tom"]
        before = chat.unread
        chat.add(models.Message(sender="tom", text="ping"))
        self.assertEqual(chat.unread, before + 1)
        chat.add(models.Message(sender="me", text="pong", status=models.SENT))
        self.assertEqual(chat.unread, before + 1, "my own message must not count as unread")
        chat.mark_read()
        self.assertEqual(chat.unread, 0)
        self.assertTrue(all(m.status == models.READ for m in chat.messages if m.mine))

    def test_pinned_chat_comes_first(self):
        store = models.Store(self.path)
        self.assertTrue(store.ordered()[0].pinned)

    def test_search_matches_names_and_message_text(self):
        store = models.Store(self.path)
        self.assertEqual([c.key for c in store.matching("Kenji")], ["kenji"])
        self.assertIn("priya", [c.key for c in store.matching("lasagne")])
        self.assertEqual(store.matching("   "), store.ordered())

    def test_picture_messages_read_well_in_a_preview(self):
        message = models.Message(sender="me", text="Yes 👍", picture="yes")
        self.assertTrue(message.preview().startswith("[Yes]"))
        self.assertIn("You said", message.spoken())

    def test_unknown_contacts_in_an_old_file_are_dropped(self):
        store = models.Store(self.path)
        store.chats["ghost"] = models.Chat(key="ghost")
        store.save()
        reloaded = models.Store(self.path)
        self.assertNotIn("ghost", reloaded.chats)

    def test_broken_file_falls_back_to_the_demo_chats(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("this is not json")
        store = models.Store(self.path)
        self.assertTrue(store.chats["amina"].messages)


class TestBots(unittest.TestCase):
    def test_every_picture_reply_uses_a_real_pictogram(self):
        for key, replies in bots.PICTURE_REPLIES.items():
            self.assertIn(key, BY_KEY, f"reply keyed on unknown pictogram {key}")
            for text, picture in replies:
                self.assertTrue(text.strip())
                if picture is not None:
                    self.assertIn(picture, BY_KEY)

    def test_persona_replies_exist_for_every_contact(self):
        for person in people.CONTACTS:
            self.assertIn(person.persona, bots.PERSONA_REPLIES)

    def test_reply_comes_from_someone_in_the_conversation(self):
        for person in people.CONTACTS:
            message = models.Message(sender="me", text="hello there, how are you?")
            reply = bots.reply_to(person, message)
            self.assertIn(reply.sender, people.BY_KEY)
            self.assertFalse(reply.mine)
            self.assertTrue(reply.text.strip() or reply.picture)

    def test_asking_for_help_is_answered_helpfully(self):
        message = models.Message(sender="me", text="", picture="help")
        reply = bots.reply_to(people.get("grace"), message)
        self.assertTrue(reply.text.strip())

    def test_typing_delay_is_sensible(self):
        message = models.Message(sender="me", text="a message with several words in it")
        self.assertGreater(bots.typing_delay(message), 500)
        self.assertLess(bots.typing_delay(message), 6000)


class TestTextUtil(unittest.TestCase):
    class FakeFont:
        def measure(self, text):
            return len(text) * 10

    def test_short_text_is_untouched(self):
        self.assertEqual(elide("hello", self.FakeFont(), 500), "hello")

    def test_long_text_is_shortened(self):
        result = elide("a very long contact name indeed", self.FakeFont(), 100)
        self.assertTrue(result.endswith("…"))
        self.assertLessEqual(self.FakeFont().measure(result), 100)


def has_display() -> bool:
    if sys.platform.startswith(("win", "darwin")):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


@unittest.skipUnless(has_display(), "needs a screen")
class TestApp(unittest.TestCase):
    """Drive the real window: build it, send messages, switch every setting."""

    @classmethod
    def setUpClass(cls):
        try:
            import tkinter  # noqa: F401
        except ModuleNotFoundError:
            raise unittest.SkipTest("tkinter is not installed")

    def setUp(self):
        import tkinter as tk

        from marasender.app import App

        self.folder = tempfile.TemporaryDirectory()
        os.environ["MARASENDER_HOME"] = self.folder.name
        self.root = tk.Tk()
        self.app = App(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.folder.cleanup()

    def test_the_app_bar_shows_the_name_one_way_or_the_other(self):
        title = self.app.bar_title
        if self.app.theme.has_display_font:
            self.assertEqual(title.cget("text"), APP_NAME)
        else:
            self.assertTrue(title.cget("image"), "no font and no drawn wordmark")

    def test_all_pictures_load(self):
        self.assertEqual(self.app.images.missing, [])

    def test_sending_a_message_shows_it_in_the_chat_and_the_list(self):
        self.app.open_chat("tom")
        self.app.send_text("Are we still meeting on Thursday?")
        self.root.update()
        chat = self.app.store.chats["tom"]
        self.assertEqual(chat.last().text, "Are we still meeting on Thursday?")
        self.assertIn("Are we still", self.app.sidebar.rows["tom"].preview.cget("text"))

    def test_a_picture_message_carries_its_picture(self):
        self.app.open_chat("grace")
        self.app.send_pictogram(BY_KEY["help"])
        self.root.update()
        self.assertEqual(self.app.store.chats["grace"].last().picture, "help")

    def test_the_contact_replies(self):
        self.app.open_chat("luca")
        message = models.Message(sender="me", text="hello!", status=models.SENT)
        self.app.store.chats["luca"].add(message)
        self.app._deliver_reply("luca", message)
        self.root.update()
        self.assertFalse(self.app.store.chats["luca"].last().mine)
        self.assertEqual(message.status, models.READ, "my message should be marked read")

    def test_every_palette_and_text_size_repaints_cleanly(self):
        for _ in range(len(theme.PALETTES)):
            self.app.cycle_palette()
            for step in (1, 1, -1, -1):
                self.app.change_text_size(step)
            self.root.update()

    def test_the_picture_board_opens_and_closes(self):
        self.app.open_board()
        self.root.update()
        self.assertTrue(self.app.board.winfo_ismapped())
        self.assertTrue(self.app.composer.winfo_ismapped())
        self.app.close_board()
        self.root.update()
        self.assertFalse(self.app.board.winfo_ismapped())

    def test_the_composer_never_gets_squeezed_off_screen(self):
        self.root.geometry("880x560")
        self.root.update()
        self.app.open_board()
        self.root.update()
        self.assertGreaterEqual(
            self.app.composer.winfo_height(),
            self.app.composer.winfo_reqheight(),
            "the picture board must not push the composer out of the window",
        )

    def test_search_filters_the_conversation_list(self):
        self.app.sidebar.search_var.set("Kenji")
        self.root.update()
        self.assertEqual(list(self.app.sidebar.rows), ["kenji"])
        self.app.sidebar.search_var.set("")
        self.root.update()
        self.assertGreater(len(self.app.sidebar.rows), 1)

    def test_switching_chats_marks_them_read(self):
        self.app.store.chats["grace"].unread = 3
        self.app.open_chat("grace")
        self.root.update()
        self.assertEqual(self.app.store.chats["grace"].unread, 0)

    def test_help_window_opens(self):
        self.app.show_help()
        self.root.update()
        self.assertTrue(any(str(w).startswith(".!toplevel") for w in self.root.winfo_children()))


if __name__ == "__main__":
    unittest.main()
