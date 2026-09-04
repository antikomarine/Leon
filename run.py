#!/usr/bin/env python3
"""Start ColorChat.

    python3 run.py

Needs nothing but Python 3.9+ with Tkinter (part of the standard library; on
Debian/Ubuntu it is the 'python3-tk' package).
"""

import sys

if sys.version_info < (3, 9):
    raise SystemExit("ColorChat needs Python 3.9 or newer.")

try:
    import tkinter  # noqa: F401
except ModuleNotFoundError:
    raise SystemExit(
        "Tkinter is missing.\n"
        "  Debian/Ubuntu:  sudo apt install python3-tk\n"
        "  Fedora:         sudo dnf install python3-tkinter\n"
        "  macOS/Windows:  it is included with python.org installers."
    )

from colorchat.app import main

if __name__ == "__main__":
    main()
