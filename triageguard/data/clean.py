"""Offset-preserving text cleaning.

Every downstream label is a character span, so cleaning must never change the
length of the text. We only swap characters one for one: exotic whitespace
becomes a plain space, curly quotes become straight quotes, and control
characters other than newline become a space. Anything that would shift
offsets (collapsing spaces, stripping lines) is left to the tokenizer.
"""

from __future__ import annotations

import unicodedata

_MAP = {
    "\t": " ", "\r": " ", " ": " ", " ": " ", " ": " ", "​": " ",
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "−": "-",
}


def clean_text(text: str) -> str:
    out = []
    for ch in text:
        if ch in _MAP:
            out.append(_MAP[ch])
        elif ch != "\n" and unicodedata.category(ch) == "Cc":
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)
