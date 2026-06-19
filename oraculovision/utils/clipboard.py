"""Clipboard helpers."""

from __future__ import annotations

import subprocess


def copy_to_clipboard(text: str) -> bool:
    """Try wl-copy, xclip, or xsel."""
    commands = [
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
    ]
    encoded = text.encode()
    for cmd in commands:
        try:
            subprocess.run(cmd, input=encoded, check=True, timeout=3)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    return False