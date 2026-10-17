"""Generate the synthetic TriageGuard corpus into data/corpus/.

Usage: python3 scripts/generate_corpus.py [--patients 1100] [--seed 13] [--out data/corpus]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from triageguard.data.generate import main  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--patients", type=int, default=1100)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--out", default="data/corpus")
    a = ap.parse_args()
    print(json.dumps(main(a.out, a.patients, a.seed), indent=2))
