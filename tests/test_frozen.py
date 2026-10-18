"""Fails if a frozen test set changed without re-running scripts/freeze_golden.py."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from freeze_golden import hashes  # noqa: E402


class FrozenTestSets(unittest.TestCase):
    def test_hashes_match(self):
        path = ROOT / "data" / "FROZEN_TEST_SETS.json"
        if not path.exists():
            self.skipTest("test sets not frozen yet")
        frozen = json.loads(path.read_text())["sha256"]
        self.assertEqual(hashes(), frozen)


if __name__ == "__main__":
    unittest.main()
