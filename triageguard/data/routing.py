"""Routing labels from several signals (M1 section 4.5).

Labels are computed only from facts that the rendered document shows, so the
label is always recoverable from the text. Several signals combine: an amount
in the ambiguous band only counts as high-value together with a long stay or
several procedures. Suspicious wins over high-value because a missed
suspicious document is the costlier error for the fraud analyst.

With a real insurer's data, human routing decisions would replace these rules
as labels.
"""

from __future__ import annotations

HIGH_VALUE = 25_000.0
AMBIGUOUS_FLOOR = 20_000.0
LONG_STAY_DAYS = 5


def signals(shown: dict) -> list[str]:
    out = []
    items = shown["line_items"]
    if len(items) != len(set(items)):
        out.append("duplicate_billing")

    adm, dis, dob = shown["admission"], shown["discharge"], shown["dob"]
    if (adm and dis and dis < adm) or (dob and any(d < dob for d in shown["service_dates"])):
        out.append("impossible_dates")

    fam = shown["diag_family"]
    if fam and any(pf != fam for pf in shown["proc_families"]):
        out.append("procedure_mismatch")
    return out


def is_high_value(shown: dict) -> bool:
    amount = shown["amount"]
    if amount is None:
        return False
    if amount >= HIGH_VALUE:
        return True
    if amount >= AMBIGUOUS_FLOOR:
        adm, dis = shown["admission"], shown["discharge"]
        long_stay = bool(adm and dis and (dis - adm).days >= LONG_STAY_DAYS)
        many_procs = len(shown["proc_families"]) >= 2 or len({d for d, _ in shown["line_items"]}) >= 4
        return long_stay or many_procs
    return False


def route(shown: dict) -> tuple[str, list[str], bool]:
    sig = signals(shown)
    hv = is_high_value(shown)
    if sig:
        return "suspicious", sig, hv
    return ("high_value" if hv else "routine"), sig, hv
