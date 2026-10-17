# TriageGuard: privacy-first insurance document triage

TriageGuard does the first sorting step a health-insurance mailroom does by hand, and does it safely. For each claim document it:

1. hides personal identifiers (names, SSNs, phones, addresses, member IDs, ...),
2. classifies the document (claim form, hospital bill, discharge summary, lab report, prescription, pre-authorization letter),
3. extracts the key fields (diagnosis, dates, amounts, provider, ...),
4. suggests a route (**routine**, **high-value** or **suspicious**), and
5. reports how confident it is, so that unsure cases go to a human.

The core idea is to never leak an identifier (PII recall comes first) and to automate only what the system is confident about. Everything is trained and tested on a synthetic corpus with exact labels. A separate hard test set (unseen layouts, heavy noise, OCR-style text) keeps the scores honest.

The full problem definition and business case is in [docs/M1_Problem_Definition_and_Business_Case.pdf](docs/M1_Problem_Definition_and_Business_Case.pdf).

**Start here:** [Architecture](docs/ARCHITECTURE.md) covers how the system and data pipeline fit together. The [plan and history](docs/PLAN.md) covers what each phase did, what was redone and why, and what comes next.

## Status

| Milestone | Deliverable | State |
|---|---|---|
| M1 Problem definition | Problem brief, users, KPIs, feasibility, repository | Done. Gaps found in review are settled in [decision_log.md](docs/decision_log.md) |
| M2 Data preparation | Synthetic corpora, data card, EDA, cleaning, splits, privacy notes, realism comparison | Done. Main dataset is Synthea + Faker |
| M3 Baselines and models | Rule and TF-IDF baselines, fine-tuned candidates, experiment log | Next (pre-M3 items in [PLAN.md](docs/PLAN.md#before-m3-open-items)) |
| M4 Evaluation | Error analysis, OCR robustness, threshold choice | Planned |
| M5 Deployment prototype | FastAPI service, Docker, monitoring, fallbacks | Planned |
| M6 Final delivery | Report, live demo, presentation | Planned |

## The corpora (M2)

There are two corpora with the same format, layouts, noise and splits, stored separately so they can be compared:

| corpus | source | documents | role |
|---|---|---|---|
| `data/corpus_synthea/` | Synthea patient histories + Faker identifiers | 5,105 from 1,096 patients | **Main dataset** |
| `data/corpus/` | In-house generator | 6,802 from 1,100 patients | Balanced, privacy-safe control set |

Synthea + Faker won the [realism comparison](docs/realism_comparison.md) on age mix, clinical plausibility, stays and costs, and vocabulary. It still needs rebalancing before M3, because it has very few discharge summaries and high-value documents (see [PLAN.md](docs/PLAN.md)).

Each corpus has four splits plus a real-scan set:

| split | Synthea + Faker | in-house | what it is for |
|---|---|---|---|
| `train` | 3,582 | 4,689 | training |
| `val` | 496 | 709 | tuning, choosing confidence thresholds |
| `test_golden` | 521 | 682 | frozen final score, never tuned on |
| `test_hard` | 506 | 722 | held-out layouts, heavy noise, OCR-style text |
| `real_ocr` | 150 | 150 | golden docs rendered to images and read back with Tesseract |

Splits are by patient, and one layout per document type appears only in `test_hard`. More detail:

* [Architecture](docs/ARCHITECTURE.md): runtime pipeline, privacy boundary, data pipeline, code map
* [Plan and history](docs/PLAN.md): phase-by-phase record, redone steps, pre-M3 checklist
* [Data card](docs/data_card.md): how the corpus is built, record format, limitations
* [EDA](docs/eda.md): distributions, PII density, routing ambiguity, vocabulary shift, leakage checks
* [Privacy notes](docs/privacy_notes.md): what is masked, the two-tier rules, why the data is safe to publish
* [Realism comparison](docs/realism_comparison.md): in-house vs Synthea + Faker against Census and HCUP reference figures
* [Decision log](docs/decision_log.md): M1 review fixes and every M2 change to the plan, including the switch to Synthea + Faker

## Quick start

M1 and M2 need only Python 3.10+ and no third-party packages.

```bash
python3 scripts/generate_corpus.py      # rebuild data/corpus/ (deterministic, about 1 second)
python3 scripts/eda.py                  # rewrite docs/eda.md and reports/eda_stats.json
python3 -m unittest -v                  # generator, routing and span tests
```

Synthea + Faker corpus, real-scan OCR sets and the realism report (need the project venv, Java and Tesseract):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/generate_synthea_corpus.py      # Synthea run command is in the script docstring
.venv/bin/python scripts/make_scans.py --n 150 --corpus data/corpus_synthea
.venv/bin/python scripts/compare_realism.py
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
    synthea_source.py  episodes from Synthea CSV output, identifiers from Faker
    generate.py        corpus assembly and patient-level splits
scripts/               generate_corpus.py, generate_synthea_corpus.py, eda.py, make_scans.py, compare_realism.py
data/corpus/           in-house corpus: train / val / test_golden / test_hard JSONL, manifest, real_ocr.jsonl
data/corpus_synthea/   Synthea + Faker corpus, same layout, plus the Synthea run metadata
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
