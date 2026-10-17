"""Corpus integrity checks. Generation fails if any of these break."""

from __future__ import annotations

import re
from collections import defaultdict

from ..schema import DOC_TYPES, FIELDS_BY_TYPE, PII_LABELS, ROUTES

_REAL_SSN = re.compile(r"\b(?!9\d\d)\d{3}-\d{2}-\d{4}\b")


def validate_doc(d: dict) -> list[str]:
    errs = []
    t = d["text"]
    did = d["doc_id"]
    if d["doc_type"] not in DOC_TYPES:
        errs.append(f"{did}: unknown doc_type {d['doc_type']}")
    if d["route"] not in ROUTES:
        errs.append(f"{did}: unknown route {d['route']}")
    prev_end = -1
    for sp in d["pii"]:
        if sp["label"] not in PII_LABELS:
            errs.append(f"{did}: unknown PII label {sp['label']}")
        if t[sp["start"]:sp["end"]] != sp["text"] or sp["start"] >= sp["end"]:
            errs.append(f"{did}: PII span text mismatch at {sp['start']}")
        if sp["start"] < prev_end:
            errs.append(f"{did}: overlapping PII spans at {sp['start']}")
        prev_end = sp["end"]
    for sp in d["field_spans"]:
        if t[sp["start"]:sp["end"]] != sp["text"]:
            errs.append(f"{did}: field span text mismatch for {sp['field']}")
    expected = set(FIELDS_BY_TYPE[d["doc_type"]])
    if set(d["fields"]) != expected:
        errs.append(f"{did}: fields {sorted(d['fields'])} != {sorted(expected)}")
    if not d["ocr"] and _REAL_SSN.search(t):
        errs.append(f"{did}: SSN outside the never-issued 900-999 range")
    return errs


def validate_corpus(docs: list[dict]) -> list[str]:
    errs = []
    seen_ids = set()
    patient_split = defaultdict(set)
    for d in docs:
        errs += validate_doc(d)
        if d["doc_id"] in seen_ids:
            errs.append(f"duplicate doc_id {d['doc_id']}")
        seen_ids.add(d["doc_id"])
        patient_split[d["patient_id"]].add(d["split"])
        if d["held_out_layout"] and d["split"] != "test_hard":
            errs.append(f"{d['doc_id']}: held-out layout leaked into {d['split']}")
        if d["ocr"] and d["split"] != "test_hard":
            errs.append(f"{d['doc_id']}: OCR text outside test_hard")
    for pid, splits in patient_split.items():
        if len(splits) > 1:
            errs.append(f"patient {pid} appears in several splits: {sorted(splits)}")
    return errs
