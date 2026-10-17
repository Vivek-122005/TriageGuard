"""Episodes from Synthea output, with identifiers filled in by Faker.

This is the second data source, built to compare against the in-house
generator (patients.py). Synthea simulates whole patient lives from public
health statistics, so diagnoses, procedures, stays, costs, lab results and
medicines come from one coherent simulated history. Synthea does not supply
phone numbers, emails, member IDs, MRNs or account numbers; Faker does
(M1 section 8.3, steps 1-2).

Mapping from Synthea CSV export to an Episode:
* candidate episodes are encounters of class inpatient, emergency,
  outpatient, ambulatory or urgent care that have a reason (a disorder or
  finding) and at least one procedure;
* each patient contributes 1-3 episodes with distinct reasons;
* diagnosis = encounter reason (SNOMED CT), procedures = the encounter's
  procedures, line items = procedure costs + encounter fee + medicines;
* labs = numeric laboratory observations of that encounter, or the patient's
  latest ones before it; medicines = those ordered in or active at it.

Warning signs are injected with the same rates and logic as patients.py so
that the two corpora differ only in where the facts come from.
"""

from __future__ import annotations

import csv
import random
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from faker import Faker

from . import vocab
from .patients import Episode, LineItem, Patient

CLASSES = {"inpatient", "emergency", "outpatient", "ambulatory", "urgentcare"}
_SUFFIX = re.compile(r"\s*\((disorder|procedure|finding|situation|regime/therapy)\)\s*$")
_STRENGTH = re.compile(r"\s(\d[\d.]*\s*(?:MG|MCG|ML|UNT|MG/ML|MG/MG|%)\S*(?:\s*/\s*\S+)?)", re.I)
STATE_ABBR = {"Massachusetts": "MA"}

# Typical adult reference ranges for the most common Synthea lab results,
# keyed by the start of the LOINC display name. Real lab reports always print
# a range, so the corpus should too.
LAB_RANGES = {
    "MCV ": (80, 100), "Hematocrit": (36, 50), "Leukocytes [#/volume] in Blood": (4.5, 11.0),
    "Erythrocytes [#/volume] in Blood": (4.2, 5.9), "Hemoglobin [Mass/volume]": (12.0, 17.5),
    "Urea nitrogen": (7, 20), "Glucose [Mass/volume] in Blood": (70, 99), "MCH ": (27, 33),
    "Cholesterol in HDL": (40, 90), "Creatinine [Mass/volume]": (0.6, 1.2), "Sodium": (135, 145),
    "Calcium": (8.5, 10.5), "Hemoglobin A1c": (4.0, 5.6), "Potassium": (3.5, 5.1),
    "Carbon dioxide": (22, 29), "Cholesterol in LDL": (0, 100), "Triglyceride": (0, 150),
    "Chloride": (98, 107), "Bilirubin.total": (0.1, 1.2), "Alkaline phosphatase": (44, 147),
    "Globulin": (20, 35), "Glomerular filtration rate": (90, 120), "Albumin [Mass/volume] in Serum": (3.5, 5.0),
    "Cholesterol [Mass/volume]": (125, 200), "Platelets [#/volume]": (150, 400),
    "Protein [Mass/volume] in Serum": (6.0, 8.3), "MCHC": (32, 36), "Aspartate aminotransferase": (10, 40),
    "Alanine aminotransferase": (7, 56), "Erythrocyte [DistWidth]": (39, 46),
}


def _lab_range(name: str):
    for prefix, rng in LAB_RANGES.items():
        if name.startswith(prefix):
            return rng
    return None, None


def _clean(desc: str) -> str:
    return re.sub(r"\s{2,}", ", ", _SUFFIX.sub("", desc)).strip()


def _strip_digits(name: str) -> str:
    return re.sub(r"\d+", "", name).strip()


def _d(ts: str) -> date:
    return datetime.fromisoformat(ts[:19]).date()


def _read(path: Path):
    with open(path, newline="") as f:
        yield from csv.DictReader(f)


def _parse_med(desc: str) -> tuple[str, str]:
    m = _STRENGTH.search(desc)
    if not m:
        return desc, "as directed"
    return desc[: m.start()].strip(), m.group(1).strip().replace("MG", "mg").replace("MCG", "mcg").replace("ML", "mL")


class SyntheaSource:
    def __init__(self, csv_dir: str | Path, seed: int = 13):
        self.dir = Path(csv_dir)
        self.rng = random.Random(seed)
        self.fake = Faker("en_US")
        self.fake.seed_instance(seed)
        self._load()

    # ------------------------------------------------------------- loading
    def _load(self):
        d = self.dir
        self.patients = {r["Id"]: r for r in _read(d / "patients.csv")}
        self.orgs = {r["Id"]: r["NAME"] for r in _read(d / "organizations.csv")}
        self.providers = {r["Id"]: _strip_digits(r["NAME"]) for r in _read(d / "providers.csv")}
        self.payers = {r["Id"]: r["NAME"] for r in _read(d / "payers.csv")}
        self.encounters = {r["Id"]: r for r in _read(d / "encounters.csv")}
        self.procs = defaultdict(list)
        for r in _read(d / "procedures.csv"):
            self.procs[r["ENCOUNTER"]].append(r)
        self.meds_by_enc = defaultdict(list)
        self.meds_by_pat = defaultdict(list)
        for r in _read(d / "medications.csv"):
            self.meds_by_enc[r["ENCOUNTER"]].append(r)
            self.meds_by_pat[r["PATIENT"]].append(r)
        self.labs_by_enc = defaultdict(list)
        self.labs_by_pat = defaultdict(list)
        for r in _read(d / "observations.csv"):
            if r["CATEGORY"] == "laboratory" and r["TYPE"] == "numeric":
                self.labs_by_enc[r["ENCOUNTER"]].append(r)
                self.labs_by_pat[r["PATIENT"]].append(r)
        self.candidates = defaultdict(list)
        for e in self.encounters.values():
            reason = e["REASONDESCRIPTION"]
            if (e["ENCOUNTERCLASS"] in CLASSES and self.procs.get(e["Id"])
                    and reason.endswith(("(disorder)", "(finding)"))):
                self.candidates[e["PATIENT"]].append(e)
        # Pool for procedure-mismatch injection: (procedure row, its encounter reason).
        self.proc_pool = [(p, e["REASONDESCRIPTION"]) for pid in self.candidates
                          for e in self.candidates[pid] for p in self.procs[e["Id"]]]

    # ------------------------------------------------------------- patients
    def make_patient(self, row: dict, idx: int) -> Patient:
        f, rng = self.fake, self.rng
        first, last = _strip_digits(row["FIRST"]), _strip_digits(row["LAST"])
        handle = f"{first}.{last}".lower().replace(" ", "").replace("'", "")
        rel_first, rel_last = f.first_name(), last if rng.random() < 0.7 else f.last_name()
        return Patient(
            patient_id=f"S{idx:05d}",
            first=first,
            last=last,
            dob=date.fromisoformat(row["BIRTHDATE"]),
            ssn=row["SSN"],  # Synthea uses the never-issued 999 area.
            phone=re.sub(r"\D", "", f.basic_phone_number())[-10:],
            email=f"{handle}{rng.choice(['', str(rng.randint(1, 99))])}@{f.free_email_domain()}",
            street=row["ADDRESS"],
            city=row["CITY"],
            state=STATE_ABBR.get(row["STATE"], row["STATE"]),
            zip=row["ZIP"] or f.zipcode(),
            member_id=f"MB-{f.numerify('#######')}",
            mrn=f"MRN{f.numerify('########')}",
            account_number=f"AC{f.numerify('#########')}",
            relative_first=rel_first,
            relative_last=rel_last,
            relative_relation=rng.choice(["spouse", "daughter", "son", "mother", "father", "sister", "brother"]),
            relative_phone=re.sub(r"\D", "", f.basic_phone_number())[-10:],
        )

    # ------------------------------------------------------------- episodes
    def _labs(self, enc: dict, pid: str) -> list:
        rows = self.labs_by_enc.get(enc["Id"]) or [
            r for r in self.labs_by_pat.get(pid, []) if r["DATE"] <= enc["START"]][-12:]
        seen, out = set(), []
        for r in rows:
            name = _clean(r["DESCRIPTION"])
            if name in seen:
                continue
            seen.add(name)
            lo, hi = _lab_range(name)
            out.append((name, round(float(r["VALUE"]), 2), r["UNITS"], lo, hi))
        return out[:6]

    def _meds(self, enc: dict, pid: str) -> list:
        rows = self.meds_by_enc.get(enc["Id"]) or [
            r for r in self.meds_by_pat.get(pid, [])
            if r["START"] <= enc["START"] and (not r["STOP"] or r["STOP"] >= enc["START"])]
        out, seen = [], set()
        for r in rows:
            name, strength = _parse_med(r["DESCRIPTION"])
            if name in seen:
                continue
            seen.add(name)
            out.append((name, strength, self.rng.choice(vocab.FREQUENCIES), self.rng.choice(vocab.DURATIONS)))
        return out[:3]

    def make_episode(self, patient: Patient, pid: str, enc: dict, idx: int, rates: dict) -> Episode:
        rng, f = self.rng, self.fake
        reason = enc["REASONDESCRIPTION"]
        procs_rows = []
        seen = set()
        for p in self.procs[enc["Id"]]:
            if p["DESCRIPTION"] not in seen:
                seen.add(p["DESCRIPTION"])
                procs_rows.append(p)
        procs_rows = procs_rows[:3]
        # A procedure's "family" is the reason it was done for; untagged
        # procedures belong to the encounter's reason.
        procedures = [(_clean(p["DESCRIPTION"]), p["CODE"], p["REASONDESCRIPTION"] or reason) for p in procs_rows]
        costs = [float(p["BASE_COST"]) for p in procs_rows]

        injected = []
        if rng.random() < rates["procedure_mismatch"]:
            for _ in range(50):
                other, other_reason = rng.choice(self.proc_pool)
                if other_reason != reason:
                    procedures[-1] = (_clean(other["DESCRIPTION"]), other["CODE"], other_reason)
                    costs[-1] = float(other["BASE_COST"])
                    injected.append("procedure_mismatch")
                    break

        admission, discharge = _d(enc["START"]), _d(enc["STOP"])
        if enc["ENCOUNTERCLASS"] != "inpatient":
            discharge = admission  # an ambulatory visit that crosses midnight is not a stay
        los = (discharge - admission).days
        items = [LineItem(name, code, round(c, 2)) for (name, code, _), c in zip(procedures, costs)]
        enc_cost = float(enc["BASE_ENCOUNTER_COST"])
        if los:
            items.append(LineItem(f"Room and board ({los} days)", "0110", round(enc_cost * los, 2)))
        else:
            items.append(LineItem(f"{enc['ENCOUNTERCLASS'].capitalize()} visit fee", "0510", round(enc_cost, 2)))
        med_cost = sum(float(m["TOTALCOST"] or 0) for m in self.meds_by_enc.get(enc["Id"], []))
        if med_cost:
            items.append(LineItem("Pharmacy", "0250", round(min(med_cost, 25000.0), 2)))
        if self.labs_by_enc.get(enc["Id"]):
            items.append(LineItem("Laboratory services", "0300", round(rng.uniform(60, 900), 2)))

        if rng.random() < rates["ambiguous_amount"]:
            target = rng.uniform(19000, 31000)
            scale = target / max(1.0, sum(i.amount for i in items))
            for it in items:
                it.amount = round(it.amount * scale, 2)

        if rng.random() < rates["duplicate_billing"]:
            dup = rng.choice(items[: len(procedures)])
            items.insert(items.index(dup) + 1, LineItem(dup.description, dup.code, dup.amount))
            injected.append("duplicate_billing")

        if rng.random() < rates["impossible_dates"]:
            injected.append("impossible_dates")
            if los and rng.random() < 0.6:
                discharge = admission - timedelta(days=rng.randint(1, 9))
            else:
                shift = (admission - patient.dob).days + rng.randint(30, 3000)
                admission -= timedelta(days=shift)
                discharge -= timedelta(days=shift)

        doctor = self.providers.get(enc["PROVIDER"], f.name()).split()
        payer = self.payers.get(enc["PAYER"], "Self-pay")
        return Episode(
            episode_id=f"SE{idx:06d}",
            patient=patient,
            diag_code=enc["REASONCODE"],
            diag_text=_clean(reason),
            diag_family=reason,
            procedures=procedures,
            admission=admission,
            discharge=discharge,
            provider=self.orgs.get(enc["ORGANIZATION"], f.company()),
            doctor_first=doctor[0],
            doctor_last=doctor[-1],
            lab=f"{f.last_name()} Clinical Laboratories",
            pharmacy=f"{f.last_name()} Pharmacy",
            insurer="Self-pay (no insurance)" if payer == "NO_INSURANCE" else payer,
            claim_number=f"CLM-{admission.year}-{f.numerify('######')}",
            line_items=items,
            labs=self._labs(enc, pid),
            meds=self._meds(enc, pid),
            collection_date=admission + timedelta(days=rng.randint(0, max(0, los))),
            prescription_date=max(admission, discharge),
            letter_date=admission - timedelta(days=rng.randint(3, 30)),
            injected=injected,
            code_system="SNOMED CT",
            proc_code_system="SNOMED CT",
        )

    def episodes(self, rates: dict):
        """Yield (patient, [episodes]) for every Synthea patient with a candidate encounter."""
        ep_idx = 0
        ids = sorted(self.candidates)
        for i, pid in enumerate(ids):
            patient = self.make_patient(self.patients[pid], i)
            by_reason = {}
            for e in self.rng.sample(self.candidates[pid], len(self.candidates[pid])):
                by_reason.setdefault(e["REASONDESCRIPTION"], e)
            encs = list(by_reason.values())[: self.rng.choices([1, 2, 3], weights=[0.65, 0.28, 0.07])[0]]
            eps = []
            for e in encs:
                eps.append(self.make_episode(patient, pid, e, ep_idx, rates))
                ep_idx += 1
            yield patient, eps

