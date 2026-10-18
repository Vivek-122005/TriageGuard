"""Build the Synthea + Faker corpus into data/corpus_synthea/.

Needs the project venv (Faker) and Synthea CSV output, produced with:
  java -jar tools/synthea/synthea-with-dependencies.jar -p 3000 -s 13 -cs 13 -r 20261017 \
       --exporter.csv.export true --exporter.fhir.export false \
       --exporter.hospital.fhir.export false --exporter.practitioner.fhir.export false \
       --exporter.years_of_history 5 --exporter.baseDirectory tools/synthea/output_v2

The jar used is release master-branch-latest at commit d9d07a6
(gh release download master-branch-latest -R synthetichealth/synthea).
-r pins Synthea's reference date so the run is reproducible on any day.

Usage: .venv/bin/python scripts/generate_synthea_corpus.py [--csv tools/synthea/output_v2/csv]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from triageguard.data.generate import generate_synthea  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="tools/synthea/output_v2/csv")
    ap.add_argument("--out", default="data/corpus_synthea")
    ap.add_argument("--seed", type=int, default=13)
    a = ap.parse_args()
    print(json.dumps(generate_synthea(a.csv, a.out, a.seed), indent=2))
