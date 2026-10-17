"""Span-aware document builder plus surface formats.

Every identifier and field value is inserted through the builder, so its
character offsets are known exactly. That is what makes the PII and field
labels exact (M1 section 8.3, step 4). Noise is applied only to the literal
text between labelled values, so offsets never drift; OCR-style corruption is
applied later in a length-preserving way (noise.py).
"""

from __future__ import annotations

import random
from datetime import date

from .noise import NoiseConfig, noisy_literal

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def fmt_date(d: date, style: str) -> str:
    if style == "us":
        return d.strftime("%m/%d/%Y")
    if style == "iso":
        return d.isoformat()
    if style == "long":
        return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"
    if style == "dmy":
        return d.strftime("%d-%b-%Y")
    if style == "dot":
        return d.strftime("%m.%d.%y")
    raise ValueError(style)


def fmt_money(x: float, style: str) -> str:
    if style == "dollar":
        return f"${x:,.2f}"
    if style == "plain":
        return f"{x:.2f}"
    if style == "usd":
        return f"USD {x:,.2f}"
    if style == "dollar_space":
        return f"$ {x:,.2f}"
    raise ValueError(style)


def fmt_name(first: str, last: str, style: str) -> str:
    if style == "first_last":
        return f"{first} {last}"
    if style == "last_first":
        return f"{last}, {first}"
    if style == "upper":
        return f"{last.upper()}, {first.upper()}"
    if style == "initial":
        return f"{first[0]}. {last}"
    raise ValueError(style)


def fmt_phone(raw: str, style: str) -> str:
    a, b, c = raw[:3], raw[3:6], raw[6:]
    return {
        "paren": f"({a}) {b}-{c}",
        "dash": f"{a}-{b}-{c}",
        "dot": f"{a}.{b}.{c}",
        "plain": f"{a}{b}{c}",
    }[style]


class DocBuilder:
    def __init__(self, rng: random.Random, noise: NoiseConfig):
        self.rng = rng
        self.noise = noise
        self.parts: list[str] = []
        self.length = 0
        self.pii_spans: list[dict] = []
        self.field_spans: list[dict] = []
        self.fields: dict = {}
        # One surface style per document, chosen like a real form would.
        self.date_style = rng.choice(["us", "us", "iso", "long", "dmy", "dot"])
        self.money_style = rng.choice(["dollar", "dollar", "plain", "usd", "dollar_space"])
        self.name_style = rng.choice(["first_last", "first_last", "last_first", "upper"])
        self.phone_style = rng.choice(["paren", "dash", "dot", "plain"])

    # -- raw text -------------------------------------------------------
    def _emit(self, s: str) -> tuple[int, int]:
        start = self.length
        self.parts.append(s)
        self.length += len(s)
        return start, self.length

    def lit(self, s: str) -> "DocBuilder":
        self._emit(noisy_literal(self.rng, s, self.noise))
        return self

    def nl(self, n: int = 1) -> "DocBuilder":
        return self.lit("\n" * n)

    # -- labelled values ------------------------------------------------
    def pii(self, label: str, value: str) -> "DocBuilder":
        start, end = self._emit(value)
        self.pii_spans.append({"label": label, "start": start, "end": end, "text": value})
        return self

    def field(self, name: str, surface: str, part: str | None = None,
              item: int | None = None, pii_label: str | None = None) -> "DocBuilder":
        """Emit a field value. A doctor's name is both a field and PII."""
        start, end = self._emit(surface)
        span = {"field": name, "start": start, "end": end, "text": surface}
        if part is not None:
            span["part"] = part
        if item is not None:
            span["item"] = item
        self.field_spans.append(span)
        if pii_label:
            self.pii_spans.append({"label": pii_label, "start": start, "end": end, "text": surface})
        return self

    # -- helpers for common value kinds ---------------------------------
    def date_(self, d: date) -> str:
        return fmt_date(d, self.date_style)

    def money(self, x: float) -> str:
        return fmt_money(x, self.money_style)

    def name(self, first: str, last: str) -> str:
        return fmt_name(first, last, self.name_style)

    def doctor(self, first: str, last: str) -> str:
        style = self.rng.choice(["dr", "dr", "md", "initial"])
        if style == "dr":
            return f"Dr. {first} {last}"
        if style == "md":
            return f"{first} {last}, MD"
        return f"Dr. {first[0]}. {last}"

    def phone(self, raw: str) -> str:
        return fmt_phone(raw, self.phone_style)

    def ssn(self, raw: str) -> str:
        return self.rng.choice([raw, raw, raw, raw.replace("-", " "), raw.replace("-", "")])

    def member_id(self, raw: str) -> str:
        d = raw[3:]
        return self.rng.choice([raw, raw, f"MB{d}", f"MB {d[:3]} {d[3:]}"])

    def mrn(self, raw: str) -> str:
        d = raw[3:]
        return self.rng.choice([raw, raw, f"MRN-{d}", d])

    def account(self, raw: str) -> str:
        d = raw[2:]
        return self.rng.choice([raw, raw, f"AC-{d}", f"{d[:3]}-{d[3:6]}-{d[6:]}"])

    def keep(self) -> bool:
        """False when a missing-field noise event drops an optional line."""
        return self.rng.random() >= self.noise.p_missing_field

    @property
    def text(self) -> str:
        return "".join(self.parts)
