"""Optional 'read aloud', using whatever speech tool the machine already has.

No extra packages: macOS has ``say``, most Linux desktops have ``spd-say`` or
``espeak``, and Windows can speak through PowerShell.  If none of them is
present the feature simply reports itself as unavailable and the button
explains why instead of failing.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading

_CANDIDATES = (
    ("say", lambda text: ["say", text]),
    ("spd-say", lambda text: ["spd-say", "-w", text]),
    ("espeak-ng", lambda text: ["espeak-ng", text]),
    ("espeak", lambda text: ["espeak", text]),
)


class Speaker:
    def __init__(self) -> None:
        self.command = None
        self.tool = None
        for tool, builder in _CANDIDATES:
            if shutil.which(tool):
                self.tool, self.command = tool, builder
                break
        if self.command is None and sys.platform.startswith("win"):
            self.tool = "powershell"
            self.command = lambda text: [
                "powershell", "-NoProfile", "-Command",
                "Add-Type -AssemblyName System.Speech;"
                "(New-Object System.Speech.Synthesis.SpeechSynthesizer)"
                ".Speak([Console]::In.ReadToEnd())",
            ]

    @property
    def available(self) -> bool:
        return self.command is not None

    def unavailable_reason(self) -> str:
        return (
            "Read aloud needs a speech program. Install 'espeak-ng' (Linux); "
            "macOS and Windows already have one built in."
        )

    def say(self, text: str) -> bool:
        """Speak in the background; never let a broken tool crash the app."""
        if not self.available or not text.strip():
            return False

        def run() -> None:
            try:
                argv = self.command(text)
                if self.tool == "powershell":
                    subprocess.run(argv, input=text, text=True, timeout=60,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.run(argv, timeout=60,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        threading.Thread(target=run, daemon=True).start()
        return True
