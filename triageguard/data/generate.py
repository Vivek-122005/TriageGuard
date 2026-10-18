"""Build the synthetic TriageGuard corpus and its splits (M1 sections 8.3-8.4).

Splits are by patient: no patient appears in more than one split. The held-out
layout (index 3 of every type) is only rendered for the hard test patients,
whose documents also carry heavy noise and, for a share, OCR-style corruption.
The golden test set is drawn from the same distribution as training and is
never used for tuning.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

from .builder import DocBuilder
from .clean import clean_text
from .layouts import HELD_OUT_LAYOUT, doc_types_for_episode, render
from .noise import CLEAN, HEAVY, LIGHT, ocr_corrupt
from .patients import make_episode, make_patient
from .routing import route
from .validate import validate_corpus

SPLIT_SHARES = [("train", 0.70), ("val", 0.10), ("test_golden", 0.10), ("test_hard", 0.10)]
SIGNAL_RATES = {"procedure_mismatch": 0.07, "duplicate_billing": 0.06, "impossible_dates": 0.05, "ambiguous_amount": 0.22}
OCR_SHARE_HARD = 0.4


def _assign_splits(rng: random.Random, n: int) -> list[str]:
    ids = list(range(n))
    rng.shuffle(ids)
    out = [""] * n
    start = 0
    for i, (name, share) in enumerate(SPLIT_SHARES):
        end = n if i == len(SPLIT_SHARES) - 1 else start + round(share * n)
        for j in ids[start:end]:
            out[j] = name
        start = end
    return out


def build_document(rng: random.Random, ep, doc_type: str, split: str, doc_id: str) -> dict:
    if split == "test_hard":
        layout = HELD_OUT_LAYOUT if rng.random() < 0.5 else rng.randrange(HELD_OUT_LAYOUT)
        noise = HEAVY
    else:
        layout = rng.randrange(HELD_OUT_LAYOUT)
        noise = LIGHT if rng.random() < 0.4 else CLEAN

    b = DocBuilder(rng, noise)
    shown = render(doc_type, b, ep, layout)
    text = clean_text(b.text)

    ocr = split == "test_hard" and rng.random() < OCR_SHARE_HARD
    if ocr:
        text = ocr_corrupt(rng, text, rate=rng.uniform(0.03, 0.09))
    pii = [dict(sp, text=text[sp["start"]:sp["end"]]) for sp in b.pii_spans]
    field_spans = [dict(sp, text=text[sp["start"]:sp["end"]]) for sp in b.field_spans]

    label, sig, hv = route(shown)
    return {
        "doc_id": doc_id,
        "patient_id": ep.patient.patient_id,
        "episode_id": ep.episode_id,
        "split": split,
        "doc_type": doc_type,
        "layout": f"{doc_type}/L{layout}",
        "held_out_layout": layout == HELD_OUT_LAYOUT,
        "noise": noise.name,
        "ocr": ocr,
        "text": text,
        "pii": sorted(pii, key=lambda s: s["start"]),
        "fields": b.fields,
        "field_spans": sorted(field_spans, key=lambda s: s["start"]),
        "route": label,
        "route_signals": sig,
        "amount_high_value": hv,
        "injected_signals": ep.injected,
    }


def generate(n_patients: int = 1100, seed: int = 13) -> list[dict]:
    rng = random.Random(seed)
    splits = _assign_splits(rng, n_patients)
    docs = []
    ep_idx = 0
    for i in range(n_patients):
        patient = make_patient(rng, i)
        for _ in range(rng.choices([1, 2, 3], weights=[0.65, 0.28, 0.07])[0]):
            ep = make_episode(rng, patient, ep_idx, SIGNAL_RATES)
            ep_idx += 1
            for doc_type in doc_types_for_episode(rng, ep):
                docs.append(build_document(rng, ep, doc_type, splits[i], f"D{len(docs):06d}"))
    return docs


def write_corpus(docs: list[dict], out_dir: Path, seed: int, n_patients: int, extra: dict | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    by_split: dict[str, list[dict]] = {}
    for d in docs:
        by_split.setdefault(d["split"], []).append(d)
    for split, rows in by_split.items():
        with open(out_dir / f"{split}.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    manifest = {
        "corpus_version": "m2-v1",
        "seed": seed,
        "n_patients": n_patients,
        "n_documents": len(docs),
        "documents_per_split": dict(Counter(d["split"] for d in docs)),
        "patients_per_split": {s: len({d["patient_id"] for d in rows}) for s, rows in by_split.items()},
        "signal_rates": SIGNAL_RATES,
        "ocr_share_in_hard": OCR_SHARE_HARD,
    }
    manifest.update(extra or {})
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main(out_dir: str = "data/corpus", n_patients: int = 1100, seed: int = 13) -> dict:
    docs = generate(n_patients, seed)
    problems = validate_corpus(docs)
    if problems:
        raise SystemExit("corpus failed validation:\n" + "\n".join(problems[:20]))
    return write_corpus(docs, Path(out_dir), seed, n_patients)


def generate_synthea(csv_dir: str, out_dir: str = "data/corpus_synthea", seed: int = 13) -> dict:
    """Same documents, layouts, noise and splits, but facts from Synthea + Faker."""
    from .synthea_source import SyntheaSource

    src = SyntheaSource(csv_dir, seed)
    rng = random.Random(seed)
    patient_eps = list(src.episodes(SIGNAL_RATES))
    splits = _assign_splits(rng, len(patient_eps))
    docs = []
    for (_patient, eps), split in zip(patient_eps, splits):
        for ep in eps:
            for doc_type in doc_types_for_episode(rng, ep):
                docs.append(build_document(rng, ep, doc_type, split, f"S{len(docs):06d}"))
    problems = validate_corpus(docs)
    if problems:
        raise SystemExit("corpus failed validation:\n" + "\n".join(problems[:20]))
    return write_corpus(docs, Path(out_dir), seed, len(patient_eps),
                        {"corpus_version": "m2-synthea-v2", "source": "Synthea d9d07a6 (CSV, -p 3000 -s 13 -r 20261017) + Faker en_US",
                         "selection": {"n_patients": 1100, "stay_share": 0.4, "max_reason_share": 0.10}})
