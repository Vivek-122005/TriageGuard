"""Tests for the synthetic corpus generator. Run: python3 -m unittest -v"""

import random
import unittest
from datetime import date

from triageguard.data.builder import DocBuilder
from triageguard.data.clean import clean_text
from triageguard.data.generate import generate
from triageguard.data.layouts import HELD_OUT_LAYOUT, RENDERERS
from triageguard.data.noise import HEAVY, LIGHT, ocr_corrupt
from triageguard.data.patients import make_episode, make_patient
from triageguard.data.routing import route
from triageguard.data.validate import validate_corpus
from triageguard.schema import FIELDS_BY_TYPE

RATES = {"procedure_mismatch": 0.0, "duplicate_billing": 0.0, "impossible_dates": 0.0, "ambiguous_amount": 0.0}


def shown(**kw):
    s = {"dob": None, "service_dates": [], "admission": None, "discharge": None,
         "amount": None, "diag_family": None, "proc_families": [], "line_items": []}
    s.update(kw)
    return s


class CorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = generate(n_patients=120, seed=3)

    def test_corpus_validates(self):
        self.assertEqual(validate_corpus(self.docs), [])

    def test_deterministic(self):
        again = generate(n_patients=120, seed=3)
        self.assertEqual([d["text"] for d in again], [d["text"] for d in self.docs])

    def test_every_split_present(self):
        self.assertEqual({d["split"] for d in self.docs}, {"train", "val", "test_golden", "test_hard"})

    def test_spans_point_at_their_text(self):
        for d in self.docs:
            for sp in d["pii"] + d["field_spans"]:
                self.assertEqual(d["text"][sp["start"]:sp["end"]], sp["text"])


class LayoutTest(unittest.TestCase):
    def test_all_layouts_render_all_fields(self):
        rng = random.Random(0)
        p = make_patient(rng, 0)
        for doc_type, fn in RENDERERS.items():
            for layout in range(HELD_OUT_LAYOUT + 1):
                for noise in (LIGHT, HEAVY):
                    ep = make_episode(rng, p, 0, RATES)
                    b = DocBuilder(rng, noise)
                    fn(b, ep, layout)
                    self.assertEqual(set(b.fields), set(FIELDS_BY_TYPE[doc_type]), (doc_type, layout))
                    self.assertTrue(b.pii_spans, (doc_type, layout))
                    for sp in b.pii_spans:
                        self.assertEqual(b.text[sp["start"]:sp["end"]], sp["text"])


class RoutingTest(unittest.TestCase):
    def test_routine(self):
        self.assertEqual(route(shown(amount=900.0))[0], "routine")

    def test_high_value_threshold(self):
        self.assertEqual(route(shown(amount=30000.0))[0], "high_value")

    def test_ambiguous_band_needs_second_signal(self):
        a, d = date(2026, 1, 1), date(2026, 1, 8)
        self.assertEqual(route(shown(amount=22000.0))[0], "routine")
        self.assertEqual(route(shown(amount=22000.0, admission=a, discharge=d))[0], "high_value")

    def test_suspicious_signals(self):
        a, d = date(2026, 1, 8), date(2026, 1, 1)
        self.assertEqual(route(shown(admission=a, discharge=d))[1], ["impossible_dates"])
        self.assertEqual(route(shown(dob=date(1990, 1, 1), service_dates=[date(1980, 1, 1)]))[1], ["impossible_dates"])
        self.assertEqual(route(shown(line_items=[("x", 1.0), ("x", 1.0)]))[1], ["duplicate_billing"])
        self.assertEqual(route(shown(diag_family="cardiac", proc_families=["ortho"]))[1], ["procedure_mismatch"])

    def test_suspicious_beats_high_value(self):
        r, _, hv = route(shown(amount=90000.0, line_items=[("x", 1.0), ("x", 1.0)]))
        self.assertEqual(r, "suspicious")
        self.assertTrue(hv)


class TextTest(unittest.TestCase):
    def test_ocr_and_clean_preserve_length(self):
        t = "Diagnosis: 1,500 Ollie – “ok”\t\n"
        self.assertEqual(len(ocr_corrupt(random.Random(1), t, 0.5)), len(t))
        self.assertEqual(len(clean_text(t)), len(t))


if __name__ == "__main__":
    unittest.main()
