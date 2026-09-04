# ColorChat

A WhatsApp-style messenger written in Python. It is built for people who find
a wall of grey text hard to read: **every contact has their own colour**, every
message can be a **picture**, and the whole interface can be made bigger,
darker or higher-contrast in one click.

Nothing but the Python standard library — no `pip install`, no accounts, no
network. The contacts are simulated and reply on your own machine.

![The main window](docs/screenshots/bright.png)

## Running it

```bash
git clone https://github.com/antikomarine/Leon.git
cd Leon
python3 run.py
```

Requirements: **Python 3.9+ with Tkinter**, which is part of the standard
library. It is already there on the python.org installers for Windows and
macOS; on Linux you may need the system package:

| System | Command |
| --- | --- |
| Debian / Ubuntu / Mint | `sudo apt install python3-tk` |
| Fedora | `sudo dnf install python3-tkinter` |
| Arch | `sudo pacman -S tk` |

## What it does

* **Conversations in colour.** Eight contacts and a group chat, each with their
  own colour running through their avatar, their name, their message bubbles
  and the tint of the chat background — so you always know where you are.
* **Picture messages.** A picture board of 30 large symbols (Yes, No, Help,
  Drink, Medicine, Bathroom, It hurts, Happy, Love, Home, Doctor …) grouped
  into categories. Tapping one sends a complete, polite sentence with the
  picture attached.
* **A messenger that behaves like one.** Message bubbles with tails, day
  separators, sent/delivered/read ticks, unread badges, a typing indicator,
  search across names *and* message text, and history that is still there when
  you reopen the app.

![The picture board](docs/screenshots/picture-board.png)

## Built for readability and for disabled users

This is the part of the app that got the most attention.

* **Pictures everywhere, words always.** 192 generated images: avatars,
  symbols, and interface icons. No button is ever a picture on its own — each
  one carries its word next to it, plus a tooltip with the same wording.
* **Never colour alone.** Every contact also has a *badge shape* — heart,
  square, triangle, star, diamond, hexagon, cross, group — stamped on their
  avatar and named next to their name, so colour-blind users have a second,
  independent cue.
* **Text size in seven steps**, from 90% to 200%, applied to every word in the
  app at once. The layout reflows: the conversation list widens, message
  bubbles rewrap, the toolbar wraps onto extra lines, and long names are
  shortened with an ellipsis rather than overlapping.
* **Three colour schemes** — Bright, Night and High contrast (black, white and
  yellow with thick outlines). Every text/background pair in every scheme is
  tested to meet the WCAG AA contrast ratio of 4.5:1, and contact colours are
  automatically lightened or darkened until they are readable on whichever
  background they land on.
* **Read aloud.** New messages, and any message you click, can be spoken using
  the speech tool the machine already has (`say` on macOS, `espeak`/`spd-say`
  on Linux, SAPI on Windows). If none is installed, the button explains that
  instead of failing.
* **Full keyboard access.** Everything — conversations, picture tiles, buttons
  — takes focus with Tab and activates with Enter or Space, and whatever has
  focus is outlined in a bright ring.
* **A running commentary.** The bar along the bottom says what just happened
  ("New message from Luca Rossi: …", "Text size is now 150% of normal"), so
  nothing changes silently.

![High contrast with large text](docs/screenshots/high-contrast-large-text.png)

## Keyboard shortcuts

| Keys | What it does |
| --- | --- |
| `Enter` | Send the message |
| `Shift` + `Enter` | Start a new line |
| `Ctrl` + `B` | Open or close the picture board |
| `Ctrl` + `K` | Jump to search |
| `Ctrl` + `+` / `Ctrl` + `-` | Bigger or smaller text |
| `Ctrl` + `T` | Next colour scheme |
| `Ctrl` + `R` | Read the last message aloud |
| `Ctrl` + `↑` / `Ctrl` + `↓` | Previous or next conversation |
| `F1` | Help |
| `Escape` | Close the picture board |

## How it is put together

```
run.py                     Start here
colorchat/
  app.py                   The main window and everything it coordinates
  theme.py                 The three palettes, fonts and text scaling
  colorutil.py             Contrast maths (WCAG), shared with the art tools
  models.py                Messages, chats and the JSON store
  people.py                The address book: colours, badges, personas
  pictograms.py            The picture vocabulary of the picture board
  bots.py                  What the simulated contacts say back
  assets.py                Loads the PNGs into Tk images
  speech.py                Optional read-aloud
  textutil.py              Ellipsis helper
  widgets/
    sidebar.py             Conversation list
    chatview.py            Message bubbles, drawn on a canvas
    composer.py            The message box, Send and Pictures buttons
    pictureboard.py        The picture board
    buttons.py             Picture-and-word buttons, focus rings, tooltips
    flowbar.py             A button row that wraps when the text grows
    scrollframe.py         Scrollable container with wheel support
assets/                    192 generated PNGs (committed)
tools/
  rasterizer.py            A tiny anti-aliased drawing library + PNG writer
  make_assets.py           Draws every avatar, symbol and icon
  make_screenshots.py      Regenerates the pictures in this README
tests/test_colorchat.py    39 tests
```

### The artwork

There are no third-party images and no image library. `tools/rasterizer.py` is
a small supersampled rasteriser (circles, polygons, strokes, arcs, rounded
rectangles) that writes PNGs with `zlib` and `struct`, and
`tools/make_assets.py` draws every avatar, symbol and icon with it. To change a
colour or add a symbol, edit `colorchat/pictograms.py` (or the drawing
functions) and run:

```bash
python3 tools/make_assets.py
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

They cover the data model and its persistence, the reply rules, the ellipsis
helper, the presence of every image the app asks for, and the contrast of every
colour pair in every palette. The tests that open a window (sending messages,
switching palettes and text sizes, the picture board, search) skip themselves
automatically when there is no display.

## Where your messages are kept

In `~/.colorchat/chats.json`. Delete that file to start again from the demo
conversations, or point `COLORCHAT_HOME` somewhere else to keep them elsewhere.

## Scope

The contacts are simulated: replies are generated on your own computer, and
nothing is sent anywhere. The Call and Video buttons are there to make the app
feel familiar, and say so when pressed.
