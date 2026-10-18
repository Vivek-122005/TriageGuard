"""Record SHA-256 hashes of every test set (M1 section 7.3: never tune on golden).

Run this only when a dataset is deliberately regenerated, and note it in
docs/PLAN.md. tests/test_frozen.py fails if a test file changes without a new
freeze, so an accidental regeneration or edit is caught.

Usage: python3 scripts/freeze_golden.py
"""

import hashlib
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ["test_golden.jsonl", "test_hard.jsonl", "real_ocr.jsonl"]


def hashes() -> dict:
    out = {}
    for corpus in ("corpus", "corpus_synthea"):
        for name in FILES:
            p = ROOT / "data" / corpus / name
            if p.exists():
                out[f"{corpus}/{name}"] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


if __name__ == "__main__":
    record = {"frozen_on": date.today().isoformat(), "sha256": hashes()}
    (ROOT / "data" / "FROZEN_TEST_SETS.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
