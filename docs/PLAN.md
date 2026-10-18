# TriageGuard work plan and history

This is the running record of the project: what each phase is for, what was done, what was changed or redone and why, and what comes next. It is updated after every step. Architecture is in [ARCHITECTURE.md](ARCHITECTURE.md). Detailed per-decision reasoning is in [decision_log.md](decision_log.md).

"Phase" and "milestone" mean the same thing here: phase 1 = M1, phase 2 = M2, and so on (the M1 document uses milestones).

## Status at a glance

| Phase | Goal | Status |
|---|---|---|
| M1 Problem definition | Problem, users, KPIs, feasibility, repo | Done (2026-10-17), with review fixes |
| M2 Data preparation | Corpus, data card, EDA, splits, privacy notes | Done; main dataset is Synthea + Faker v2 (rebalanced 2026-10-18) |
| M3 Baselines and models | Baselines for every stage, stronger candidates, experiment log | Next: evaluation harness, then baselines |
| M4 Evaluation and optimisation | Error analysis, OCR robustness, thresholds, calibration | Planned |
| M5 Deployment prototype | FastAPI + Docker, monitoring, fallbacks | Planned |
| M6 Final delivery | Report, live demo, presentation, viva | Planned |

## M1: Problem definition

**Goal:** decide what "good" means before building anything.

**Done**
- Problem, users, business objective and KPI targets: the PDF in `docs/`.
- Public repository: https://github.com/Vivek-122005/TriageGuard, with README, licence (MIT) and package layout.
- Review of the M1 document. Eight gaps were found and settled (details in [decision_log.md](decision_log.md#m1-review-gaps-found-and-how-they-are-settled)):
  1. How PII recall counts a hit: leak-based (every character must be masked), plus exact-span recall as a secondary measure.
  2. Field F1 for list fields: each list item is scored as its own field.
  3. Calibration metric: ECE with 15 bins.
  4. Routing is per document, using only what that document shows.
  5. Doctor names are both PII and a field.
  6. Routing needs date of birth, so it runs inside the protected area.
  7. De-identification paper citations were added.
  8. The PDF cover still says "[Your name]". **Open:** to fix before resubmitting.

**Targets (unchanged):** PII recall at least 0.97, doc-type macro-F1 at least 0.95, field F1 at least 0.90, routing recall at least 0.90, ECE at most 0.05, p95 latency under 2 s on CPU, auto-triage at least 70%.

## M2: Data preparation

**Goal:** a labelled corpus with exact PII spans, types, fields and routes, plus honest test sets.

### Step 1: in-house generator (done, kept)

- Built `triageguard/data/`: patients and episodes from hand-written lists, 6 types x 4 layouts, span-aware builder, noise, OCR-style corruption, multi-signal routing, validation, patient-level splits.
- Result: `data/corpus/`, 6,802 docs from 1,100 patients, plus EDA, data card and privacy notes.
- **Why our own generator first:** at that point Synthea (Java plus a 200 MB download), Faker and Pillow were not installed. The goal was a zero-install, fully reproducible M2. This was a deliberate change from the M1 plan and was logged as one.

### Step 2: review findings fixed inside step 1

| Found | Fix |
|---|---|
| No field was ever missing, though M1 asked for missing-field noise | Optional lines (provider, ordering physician, address and others) can be dropped |
| SSN, member ID, MRN and account numbers had one format each | 3 surface formats each |
| Relatives shared the patient's phone | Relatives get their own number |
| Specialty hospitals treated unrelated conditions (a cancer institute for AFib) | Providers chosen by clinical family |

### Step 3: Synthea + Faker corpus (done, now the main dataset)

- **Changed because:** the project owner asked for the M1 plan's Synthea + Faker data, stored separately, to compare against ours.
- Set up the project `.venv` (Faker, Pillow) and ran Synthea (`d9d07a6`, seed 13, 1,263 simulated patients, 5 years of history).
- Wrote `synthea_source.py`. It turns Synthea encounters into the same Episode objects, so layouts, noise, injection and splits are shared and only the facts differ.
- **Redone or adjusted while building it:**
  - Ambulatory visits crossing midnight were becoming one-day "stays". Only inpatient encounters count as stays now.
  - Codes were printed as ICD-10/CPT although Synthea uses SNOMED. The code system is now printed per source.
  - Lab reports had no reference ranges. Ranges were added for the 30 most common Synthea tests.
  - Prescriptions and lab reports could be empty. They are only generated when the episode has medicines or labs.
  - All of these changes leave the in-house corpus byte-for-byte unchanged (checked).
- Result: `data/corpus_synthea/`, 5,105 docs from 1,096 patients.

### Step 4: real OCR (done)

- **Changed because:** OCR was first simulated (one-for-one character swaps) since Tesseract was missing. Now that Tesseract and Pillow are installed, `make_scans.py` renders 150 golden docs per corpus and reads them back with real OCR (`real_ocr.jsonl`). The simulated OCR stays in `test_hard` because it keeps spans exact.
- About 86% of identifier strings survive real OCR unchanged in both corpora. The redactor must catch the other 14% in their corrupted form.

### Step 5: realism comparison and the main-dataset decision (done)

- `scripts/compare_realism.py` checks both corpora against the 2020 Census, HCUP stay figures and clinical common sense ([realism_comparison.md](realism_comparison.md)).
- Synthea + Faker is more realistic on age mix, clinical plausibility, stays and costs, vocabulary and identifier formats. The in-house corpus wins on common names, geographic spread, class balance and publishing safety.
- **Decision (2026-10-17, project owner):** Synthea + Faker becomes the main dataset. The in-house corpus stays as a control set and for cross-source transfer tests.

### Step 6: rebalancing the main dataset (done, 2026-10-18)

- **Changed because:** in v1 the golden test set had 3 discharge summaries and 38 high-value documents, and gingivitis was 37% of episodes. No score on those classes would have meant anything. The project owner approved the fix.
- **Redone:**
  - Synthea was re-run with 3,000 living patients (3,474 in total) and a pinned reference date (`-r 20261017`), so it can be reproduced.
  - Sampling now gives 40% of the 1,100 places to patients who had a hospital stay, and caps every diagnosis at about 10% of episodes (`SyntheaSource.select`).
  - Inpatient encounters may have a "situation" reason (for example "Awaiting transplantation of kidney").
  - Synthea's generator-style names were replaced by Faker `en_US` names matched to sex. Phones moved into the fictional 555-01xx block, and emails onto reserved domains.
- **Result:** `m2-synthea-v2`, 5,591 docs from 1,100 patients. Discharge summaries went from 42 to 470, the top diagnosis from 37% to about 11%, and distinct diagnoses from 58 to 75. Realism re-checked in [realism_comparison.md](realism_comparison.md). Stays are now deliberately over-represented (28% of episodes).
- **Still weak:** high-value documents (39 in golden, 376 in train) because Synthea stays are cheap next to the $25,000 line. Accepted for now; a 39-document recall has a wide margin of error, and M4 should report it with a confidence interval.

### Step 7: test sets frozen (done, 2026-10-18)

- `scripts/freeze_golden.py` stores SHA-256 hashes of every golden, hard and real-OCR file in `data/FROZEN_TEST_SETS.json`. `tests/test_frozen.py` fails if any of them changes without a new freeze. Any future re-freeze must be logged here.

## Before M3: open items

| # | Item | Why it matters | Needs the owner's go-ahead? |
|---|---|---|---|
| 1 | ~~Rebalance the Synthea corpus~~ | Done (step 6) | |
| 2 | ~~Pin the Synthea run~~ | Done (step 6) | |
| 3 | ~~Freeze the test sets~~ | Done (step 7) | |
| 4 | Write the evaluation harness before any model | Metrics are defined once, as settled in M1 review | No |
| 5 | Install M3 libraries in `.venv` (scikit-learn first; PyTorch, Transformers, MLflow for fine-tuning) | PyTorch support for Python 3.14 needs checking; fall back to 3.12 if missing | Yes (installs) |
| 6 | GPU for fine-tuning: Lightning AI over SSH | The owner has Lightning credits. They run Lightning's SSH setup on the Mac themselves and share only the host name, never a key. Baselines run locally on CPU. | Owner sets up SSH |
| 7 | Small real-text sanity check (M1 section 8.5) | Shows how far synthetic scores are from reality | Later (M4) |
| 8 | Fill in the name on the M1 PDF | Submission | Owner |

## M3: Baselines and models (planned)

Order of work: evaluation harness, then rule and TF-IDF baselines for every stage, then stronger models that must beat their baselines on the golden set.

| Stage | Baseline | Stronger candidate | Primary metric |
|---|---|---|---|
| PII redaction | Regex + word lists | Token NER (DistilBERT/BERT-style) + rules union | Leak-based recall per label |
| Document type | TF-IDF + logistic regression | Fine-tuned small encoder | Macro-F1 |
| Field extraction | Rules per layout family | Token tagger on field spans | Field-level F1 |
| Routing | Rules over extracted fields | Gradient-boosted or linear model over fields + text | Recall on high_value and suspicious |

Every model is trained on Synthea + Faker train data and scored on golden, hard and real OCR for both corpora (cross-source transfer). Experiments are logged with data version, parameters and scores.

## M4 to M6 (planned)

- **M4:** error analysis, OCR robustness (simulated and real), threshold sweep (automation vs error), calibration (ECE), choose the confidence gate.
- **M5:** FastAPI + Docker, `/triage` and `/health`, latency measurement, model registry, fallbacks, monitoring plan.
- **M6:** technical report, live demo, business presentation, replace the 3-minute-per-document assumption with a sourced figure.

## Change log

| Date | Change |
|---|---|
| 2026-10-17 | Repo created; M2 in-house corpus, EDA, data card, privacy notes, decision log |
| 2026-10-17 | Synthea + Faker corpus, real Tesseract OCR sets, realism comparison |
| 2026-10-17 | Synthea + Faker chosen as main dataset; ARCHITECTURE.md and PLAN.md added |
| 2026-10-18 | Synthea re-run (pinned), main dataset rebalanced to v2, names and contacts fixed, test sets frozen, EDA for both corpora |
