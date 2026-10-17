"""Noise models for the synthetic corpus (M1 section 8.3, steps 7 and 8).

Two kinds of noise:

* Literal noise is applied while a document is built and only touches the
  text between labelled values: typos, abbreviations, odd line breaks and
  spacing. Missing fields are handled by DocBuilder.keep().
* OCR-style noise is applied to the finished text. It only swaps characters
  one for one (O->0, l->1, S->5, ...), so every span offset stays valid; the
  span's surface text is refreshed afterwards. It mimics the errors M1 section
  9 lists ("Diagn0sis", "l,5OO"). Real Tesseract output can be produced with
  scripts/make_scans.py when Tesseract is installed.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NoiseConfig:
    name: str = "clean"
    p_typo: float = 0.0          # per word
    p_abbrev: float = 0.0        # per abbreviable phrase
    p_linebreak: float = 0.0     # per newline / separator
    p_missing_field: float = 0.0  # per optional line
    p_case: float = 0.0          # per literal chunk


CLEAN = NoiseConfig()
LIGHT = NoiseConfig("light", p_typo=0.01, p_abbrev=0.15, p_linebreak=0.05, p_missing_field=0.03, p_case=0.02)
HEAVY = NoiseConfig("heavy", p_typo=0.04, p_abbrev=0.45, p_linebreak=0.15, p_missing_field=0.08, p_case=0.08)

ABBREVIATIONS = {
    "Patient": ["Pt", "Pt."],
    "patient": ["pt", "pt."],
    "Diagnosis": ["Dx", "Diag."],
    "diagnosis": ["dx"],
    "Date of Birth": ["DOB", "D.O.B."],
    "Admission Date": ["Adm Date", "Adm. Dt"],
    "Discharge Date": ["Disch Date", "D/C Date"],
    "Admitted": ["Adm", "Adm."],
    "Discharged": ["Disch", "D/C"],
    "Number": ["No.", "#"],
    "Procedure": ["Proc", "Proc."],
    "procedure": ["proc"],
    "Telephone": ["Tel", "Ph"],
    "Phone": ["Ph", "Tel"],
    "Address": ["Addr", "Addr."],
    "Amount": ["Amt", "Amt."],
    "Prescription": ["Rx"],
    "history": ["hx"],
    "with": ["w/"],
    "without": ["w/o"],
    "Medical Record Number": ["MRN", "Med Rec No"],
    "Social Security Number": ["SSN", "SS#"],
}
_ABBREV_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, ABBREVIATIONS), key=len, reverse=True)) + r")\b")
_WORD_RE = re.compile(r"[A-Za-z]{4,}")


def _typo(rng: random.Random, w: str) -> str:
    i = rng.randrange(1, len(w) - 1)
    op = rng.choice(["swap", "drop", "double", "sub"])
    if op == "swap":
        return w[:i] + w[i + 1] + w[i] + w[i + 2:]
    if op == "drop":
        return w[:i] + w[i + 1:]
    if op == "double":
        return w[:i] + w[i] + w[i:]
    return w[:i] + rng.choice("aeioustnr") + w[i + 1:]


def noisy_literal(rng: random.Random, s: str, cfg: NoiseConfig) -> str:
    if cfg.name == "clean" or not s.strip():
        return s
    if cfg.p_abbrev:
        s = _ABBREV_RE.sub(lambda m: rng.choice(ABBREVIATIONS[m.group(1)]) if rng.random() < cfg.p_abbrev else m.group(1), s)
    if cfg.p_typo:
        s = _WORD_RE.sub(lambda m: _typo(rng, m.group(0)) if rng.random() < cfg.p_typo else m.group(0), s)
    if cfg.p_linebreak:
        def lb(m):
            if rng.random() >= cfg.p_linebreak:
                return m.group(0)
            return rng.choice(["\n\n", " \n", "\n   ", "  "]) if m.group(0) == "\n" else rng.choice([":", ":   ", " : ", ":\n"])
        s = re.sub(r"\n|: ", lb, s)
    if cfg.p_case and rng.random() < cfg.p_case:
        s = s.upper() if rng.random() < 0.5 else s.lower()
    return s


# One-for-one confusions that Tesseract commonly makes on degraded scans.
OCR_CONFUSIONS = {
    "O": "0", "0": "O", "o": "0", "l": "1", "1": "l", "I": "l", "i": "l",
    "S": "5", "5": "S", "B": "8", "8": "B", "Z": "2", "2": "Z", "g": "9",
    "e": "c", "a": "o", "c": "e", ",": ".", ".": ",",
    "m": "n", "h": "b", "G": "6", "6": "G", "u": "v", "t": "f",
}


def ocr_corrupt(rng: random.Random, text: str, rate: float) -> str:
    out = []
    for ch in text:
        sub = OCR_CONFUSIONS.get(ch)
        if sub and rng.random() < rate:
            out.append(sub)
        elif ch.isalnum() and rng.random() < rate / 15:
            out.append(rng.choice(["~", "'", " "]))
        else:
            out.append(ch)
    result = "".join(out)
    assert len(result) == len(text)
    return result
