"""Helpers for displaying untrusted text safely in the terminal."""
import unicodedata

_BIDI_CONTROLS = {
    "\u061c", "\u200e", "\u200f", "\u202a", "\u202b", "\u202c",
    "\u202d", "\u202e", "\u2066", "\u2067", "\u2068", "\u2069",
}


def safe_terminal_text(value):
    """Remove terminal control and bidi-formatting characters from untrusted text."""
    return "".join(
        char for char in str(value)
        if (char in "\n\t" or unicodedata.category(char) != "Cc")
        and char not in _BIDI_CONTROLS
    )
