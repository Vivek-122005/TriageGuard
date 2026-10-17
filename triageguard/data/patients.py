"""Synthetic patients and care episodes.

A patient owns the Tier 1 identifiers. An episode is one course of care
(diagnosis, procedures, dates, money) from which several documents are
rendered, so the claim form, bill and discharge summary of one episode tell a
consistent story. Warning signs (duplicate billing, impossible dates,
procedure mismatch) are injected at the episode level and only show up in a
document's label if the document actually renders the facts that reveal them
(see routing.py).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from . import vocab


@dataclass
class Patient:
    patient_id: str
    first: str
    last: str
    dob: date
    ssn: str
    phone: str
    email: str
    street: str
    city: str
    state: str
    zip: str
    member_id: str
    mrn: str
    account_number: str
    relative_first: str
    relative_last: str
    relative_relation: str
    relative_phone: str

    @property
    def address(self) -> str:
        return f"{self.street}, {self.city}, {self.state} {self.zip}"


@dataclass
class LineItem:
    description: str
    code: str
    amount: float


@dataclass
class Episode:
    episode_id: str
    patient: Patient
    diag_code: str
    diag_text: str
    diag_family: str
    procedures: list  # list of (name, code, family)
    admission: date
    discharge: date
    provider: str
    doctor_first: str
    doctor_last: str
    lab: str
    pharmacy: str
    insurer: str
    claim_number: str
    line_items: list = field(default_factory=list)
    labs: list = field(default_factory=list)  # (test, value, unit, ref_low, ref_high)
    meds: list = field(default_factory=list)  # (name, strength, frequency, duration)
    collection_date: date | None = None
    prescription_date: date | None = None
    letter_date: date | None = None
    injected: list = field(default_factory=list)

    @property
    def total(self) -> float:
        return round(sum(li.amount for li in self.line_items), 2)

    @property
    def length_of_stay(self) -> int:
        return (self.discharge - self.admission).days


def _digits(rng: random.Random, n: int) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(n))


def make_patient(rng: random.Random, idx: int) -> Patient:
    first = rng.choice(vocab.FIRST_NAMES)
    last = rng.choice(vocab.LAST_NAMES)
    dob = date(1935, 1, 1) + timedelta(days=rng.randint(0, 365 * 70))
    city, state, zip3 = rng.choice(vocab.CITIES)
    handle = f"{first}.{last}".lower().replace(" ", "").replace("'", "")
    if rng.random() < 0.5:
        handle += str(rng.randint(1, 99))
    return Patient(
        patient_id=f"P{idx:05d}",
        first=first,
        last=last,
        dob=dob,
        # 900-999 area numbers are never issued, so these can't be real SSNs.
        ssn=f"{rng.randint(900, 999)}-{_digits(rng, 2)}-{_digits(rng, 4)}",
        phone=f"555{rng.randint(100, 999)}{_digits(rng, 4)}",
        email=f"{handle}@{rng.choice(vocab.EMAIL_DOMAINS)}",
        street=f"{rng.randint(10, 9999)} {rng.choice(vocab.STREET_NAMES)} {rng.choice(vocab.STREET_SUFFIXES)}",
        city=city,
        state=state,
        zip=f"{zip3}{_digits(rng, 2)}",
        member_id=f"MB-{_digits(rng, 7)}",
        mrn=f"MRN{_digits(rng, 8)}",
        account_number=f"AC{_digits(rng, 9)}",
        relative_first=rng.choice(vocab.FIRST_NAMES),
        relative_last=last if rng.random() < 0.7 else rng.choice(vocab.LAST_NAMES),
        relative_relation=rng.choice(["spouse", "daughter", "son", "mother", "father", "sister", "brother"]),
        relative_phone=f"555{rng.randint(100, 999)}{_digits(rng, 4)}",
    )


def _procs_for_family(family: str):
    return [p for p in vocab.PROCEDURES if p[2] == family]


def make_episode(rng: random.Random, patient: Patient, idx: int, signal_rates: dict) -> Episode:
    code, wordings, family = rng.choice(vocab.DIAGNOSES)
    pool = _procs_for_family(family)
    n_procs = rng.choices([1, 2, 3], weights=[0.55, 0.32, 0.13])[0]
    chosen = rng.sample(pool, min(n_procs, len(pool)))

    injected = []
    if rng.random() < signal_rates["procedure_mismatch"]:
        other = rng.choice([p for p in vocab.PROCEDURES if p[2] != family])
        chosen[-1] = other
        injected.append("procedure_mismatch")

    inpatient = any(p[4] for p in chosen) or rng.random() < 0.15
    admission = date(2025, 1, 1) + timedelta(days=rng.randint(0, 600))
    los = rng.randint(1, 12) if inpatient else 0
    discharge = admission + timedelta(days=los)

    # Money: procedure costs, room and board, pharmacy, labs.
    items = []
    for name, pcode, _fam, (lo, hi), _inp in chosen:
        items.append(LineItem(name, pcode, round(rng.uniform(lo, hi), 2)))
    if los:
        rate = rng.choice([1450, 1800, 2200, 2650, 3100])
        items.append(LineItem(f"Room and board ({los} days)", "0110", float(rate * los)))
    if rng.random() < 0.7:
        items.append(LineItem("Pharmacy", "0250", round(rng.uniform(40, 2400), 2)))
    if rng.random() < 0.6:
        items.append(LineItem("Laboratory services", "0300", round(rng.uniform(60, 1500), 2)))

    # Push some totals into the ambiguous band around the high-value line so
    # routing cannot be learned from one amount threshold alone.
    if rng.random() < signal_rates["ambiguous_amount"]:
        target = rng.uniform(19000, 31000)
        scale = target / max(1.0, sum(i.amount for i in items))
        for it in items:
            it.amount = round(it.amount * scale, 2)

    if rng.random() < signal_rates["duplicate_billing"]:
        dup = rng.choice(items[: len(chosen)])
        items.insert(items.index(dup) + 1, LineItem(dup.description, dup.code, dup.amount))
        injected.append("duplicate_billing")

    if rng.random() < signal_rates["impossible_dates"]:
        injected.append("impossible_dates")
        if los and rng.random() < 0.6:
            # Discharged before admitted.
            discharge = admission - timedelta(days=rng.randint(1, 9))
        else:
            # Service before the patient was born.
            shift = (admission - patient.dob).days + rng.randint(30, 3000)
            admission -= timedelta(days=shift)
            discharge -= timedelta(days=shift)

    labs = []
    for test, unit, lo, hi in rng.sample(vocab.LAB_TESTS, rng.randint(2, 6)):
        span = hi - lo if hi > lo else 1
        if rng.random() < 0.35:
            val = hi + rng.uniform(0.05, 1.0) * span
        else:
            val = rng.uniform(lo, hi)
        labs.append((test, round(val, 2), unit, lo, hi))

    med_pool = [m for m in vocab.MEDICINES if m[2] == family] or vocab.MEDICINES
    meds = []
    for name, strengths, _fam in rng.sample(med_pool, min(len(med_pool), rng.randint(1, 3))):
        meds.append((name, rng.choice(strengths), rng.choice(vocab.FREQUENCIES), rng.choice(vocab.DURATIONS)))

    return Episode(
        episode_id=f"E{idx:06d}",
        patient=patient,
        diag_code=code,
        diag_text=rng.choice(wordings),
        diag_family=family,
        procedures=[(p[0], p[1], p[2]) for p in chosen],
        admission=admission,
        discharge=discharge,
        provider=rng.choice(vocab.PROVIDERS_GENERAL + vocab.PROVIDERS_SPECIALTY.get(family, []) * 2),
        doctor_first=rng.choice(vocab.FIRST_NAMES),
        doctor_last=rng.choice(vocab.LAST_NAMES),
        lab=rng.choice(vocab.LABS),
        pharmacy=rng.choice(vocab.PHARMACIES),
        insurer=rng.choice(vocab.INSURERS),
        claim_number=f"CLM-{admission.year}-{_digits(rng, 6)}",
        line_items=items,
        labs=labs,
        meds=meds,
        collection_date=admission + timedelta(days=rng.randint(0, max(0, los))),
        prescription_date=max(admission, discharge),
        letter_date=admission - timedelta(days=rng.randint(3, 30)),
        injected=injected,
    )
