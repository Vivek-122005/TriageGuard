# TriageGuard: privacy-first insurance document triage

TriageGuard does the first sorting step a health-insurance mailroom does by hand, and does it safely. For each claim document it:

1. hides personal identifiers (names, SSNs, phones, addresses, member IDs, ...),
2. classifies the document (claim form, hospital bill, discharge summary, lab report, prescription, pre-authorization letter),
3. extracts the key fields (diagnosis, dates, amounts, provider, ...),
4. suggests a route (**routine**, **high-value** or **suspicious**), and
5. reports how confident it is, so that unsure cases go to a human.

The core idea is to never leak an identifier (PII recall comes first) and to automate only what the system is confident about. Everything is trained and tested on a synthetic corpus with exact labels. A separate hard test set (unseen layouts, heavy noise, OCR-style text) keeps the scores honest.

The full problem definition and business case is in [docs/M1_Problem_Definition_and_Business_Case.pdf](docs/M1_Problem_Definition_and_Business_Case.pdf).

## Status

| Milestone | Deliverable | State |
|---|---|---|
| M1 Problem definition | Problem brief, users, KPIs, feasibility, repository | Done. Gaps found in review are settled in [decision_log.md](docs/decision_log.md) |
| M2 Data preparation | Synthetic corpus, data card, EDA, cleaning, splits, privacy notes | Done |
| M3 Baselines and models | Rule and TF-IDF baselines, fine-tuned candidates, experiment log | Next |
| M4 Evaluation | Error analysis, OCR robustness, threshold choice | Planned |
| M5 Deployment prototype | FastAPI service, Docker, monitoring, fallbacks | Planned |
| M6 Final delivery | Report, live demo, presentation | Planned |

## The corpus (M2)

6,802 documents from 1,100 synthetic patients, labelled with PII spans, document type, fields (values and spans) and route.

| split | documents | what it is for |
|---|---|---|
| `train` | 4,689 | training |
| `val` | 709 | tuning, choosing confidence thresholds |
| `test_golden` | 682 | frozen final score, never tuned on |
| `test_hard` | 722 | held-out layouts, heavy noise, OCR-style text |

Splits are by patient, and one layout per document type appears only in `test_hard`. More detail:

* [Data card](docs/data_card.md): how the corpus is built, record format, limitations
* [EDA](docs/eda.md): distributions, PII density, routing ambiguity, vocabulary shift, leakage checks
* [Privacy notes](docs/privacy_notes.md): what is masked, the two-tier rules, why the data is safe to publish
* [Decision log](docs/decision_log.md): M1 review fixes and M2 changes to the plan (including why Synthea was not used)

## Quick start

M1 and M2 need only Python 3.10+ and no third-party packages.

```bash
python3 scripts/generate_corpus.py      # rebuild data/corpus/ (deterministic, about 1 second)
python3 scripts/eda.py                  # rewrite docs/eda.md and reports/eda_stats.json
python3 -m unittest -v                  # generator, routing and span tests
```

Optional real-scan set (needs `pip install pillow` and Tesseract):

```bash
python3 scripts/make_scans.py --n 150
```

## Repository layout

```
triageguard/
  schema.py            label sets shared by every stage (PII labels, types, fields, routes)
  data/
    vocab.py           names, places, diagnoses, procedures, labs, medicines
    patients.py        synthetic patients and care episodes, injected warning signs
    builder.py         span-aware document builder and surface formats
    layouts.py         4 layouts x 6 document types (layout 3 held out)
    noise.py           typos, abbreviations, layout noise, OCR-style confusions
    routing.py         multi-signal routing labels from visible facts
    clean.py           offset-preserving text cleaning
    validate.py        integrity and leakage checks (generation fails on any error)
    generate.py        corpus assembly and patient-level splits
scripts/               generate_corpus.py, eda.py, make_scans.py
data/corpus/           train / val / test_golden / test_hard JSONL + manifest.json
docs/                  M1 PDF, data card, EDA, privacy notes, decision log
reports/               machine-readable EDA numbers
tests/                 unit tests
```

## Success targets (from M1)

| Stage | Metric | Target |
|---|---|---|
| PII redaction | entity-level recall | at least 0.97 |
| Document type | macro-F1 | at least 0.95 |
| Field extraction | field-level F1 | at least 0.90 |
| Routing | recall on high-value and suspicious | at least 0.90 |
| Confidence | expected calibration error | at most 0.05 |
| System | p95 latency per document on CPU | under 2 s |
| Business | auto-triage rate at high accuracy | at least 70% |

No real patient data is used anywhere in this repository.
