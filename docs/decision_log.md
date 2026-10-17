# Decision log

Continues M1 section 15. Each entry: what changed, why, and what it affects. Targets are never lowered silently (M1 section 7.3).

## M1 decisions (from the M1 document)

| Decision | Reason |
|---|---|
| Industry Track | End-to-end system, not a paper reproduction |
| US-style documents (HIPAA as guidance) | More public tooling; identifier list is configurable |
| Synthetic corpus | No public claim data exists; exact labels, clean licences |
| Text-first, OCR tested | NLP focus; OCR is a separate upstream service in real systems |
| Two-tier PII | Extraction needs dates and amounts; the safe copy still protects identifiers |
| "Suspicious", not "fraud" | No real fraud labels |
| Baseline before advanced models | A stronger model ships only if it beats the baseline on the golden set |
| Human review for low confidence | Wrong routing is costly |

## M1 review: gaps found and how they are settled

| # | Gap in the M1 document | Resolution |
|---|---|---|
| 1 | Cover page still says "Prepared by: [Your name]" | Fill in before the PDF is resubmitted. Kept as-is in `docs/` because the PDF is the submitted artefact. |
| 2 | "Entity-level recall" for PII does not say what counts as found | **Primary:** an identifier counts as found only if every character of it is masked (leak-based, matches the privacy goal). **Secondary:** exact-span recall and precision per label. |
| 3 | Field-level F1 is undefined for list fields (line items, tests, medicines) | Each list element is scored as its own field instance. Values are compared after normalisation (ISO dates, amounts to the cent, case-insensitive text). |
| 4 | Calibration error metric not specified | Expected calibration error with 15 equal-width bins on the top-class probability. |
| 5 | Routing is described per claim, but most documents carry no amount | Routing is per document and uses only what the document shows. Lab reports, prescriptions and discharge summaries can be routine or suspicious, never high-value. |
| 6 | Doctor names are both PII and a field | Labelled as both. The field is used only inside the protected area. See [privacy_notes.md](privacy_notes.md). |
| 7 | Routing needs date of birth (impossible dates) but DOB is masked | Routing runs on raw text inside the protected area and emits only signal names. |
| 8 | Section 7.2 promises published de-identification scores "in M2" | Cited below. |

Published reference points for the PII recall target of at least 0.97:

* Dernoncourt, Lee, Uzuner, Szolovits (2017). *De-identification of patient notes with recurrent neural networks.* JAMIA 24(3). Reports F1 of 97.85 on i2b2 2014 and 99.23 on MIMIC.
* Stubbs, Kotfila, Uzuner (2015). *Automated systems for the de-identification of longitudinal clinical narratives: Overview of 2014 i2b2/UTHealth shared task Track 1.* J. Biomed. Inform. 58. The best shared-task system scored about 0.94 F1 on the strict measure.

Those benchmarks use free clinical narrative, which is harder than our mostly structured forms, so at least 0.97 recall is a reasonable floor on the golden set. It is not realistic on the hard set without the OCR improvements planned for M4.

## M2 decisions

| Decision | Reason | Affects |
|---|---|---|
| **In-house patient generator instead of Synthea** (change from M1 section 8.3, step 1; Synthea was added later as a second corpus, see below) | Synthea needs Java plus a large download and produces detailed clinical histories we do not use. What we need (identifiers, one episode, consistent amounts and dates) is about 150 lines of seeded Python with no dependencies. This also follows the M1 Plan B spirit of controlling data-work risk. Synthea can still be dropped in later behind `make_episode`. | Data card; clinical realism is simpler |
| **Faker not used** | Same reason. Fixed word lists keep generation dependency-free and reproducible. Generated identifiers sit in never-issued ranges (900-999 SSNs, 555 phones), which Faker does not guarantee. | Name variety is lower; M3 tests unseen names |
| **Four layouts per type, layout 3 held out** | M1 asked for three to four. Four leaves three for training. | Hard test set |
| **Splits 70/10/10/10 by patient** (train / val / golden / hard) | The hard set uses its own patients, so held-out layouts and noise never share a patient with training. | All evaluation |
| **Corpus size: 1,100 patients, 6,802 documents** | Inside the planned 5,000-8,000. Enough for 6-way classification and token NER, and fast to regenerate (about 1 second). | Confirms M1 section 8.3 |
| **OCR-style noise is simulated and length-preserving; real Tesseract is a separate script** | Tesseract is not installed on the dev machine. Simulated confusions keep exact spans, so PII recall stays measurable on OCR-like text. `scripts/make_scans.py` produces real OCR text once Tesseract and Pillow are installed. | M4 robustness test has two OCR sets |
| **Routing labels from visible facts only** | A label must be recoverable from the text. 476 documents from episodes with an injected sign do not show it and are labelled accordingly. | Routing stage |
| **Ambiguous band $20k-$25k** needs a second signal (5+ day stay, 2+ procedures, or 4+ line items) | Prevents routing from collapsing to one threshold (M1 section 4.5). About half the documents in the band are high-value. | Routing stage |
| **Offset-preserving cleaning** (`clean.py`) | Every label is a character span, so cleaning must not change length. Whitespace collapsing is left to the tokenizer. | All stages |
| **Corpus committed to Git** | About 14 MB. Graders and later milestones get the exact data without running anything; the seed reproduces it. | Repository size |

## Synthea + Faker corpus (added after review)

| Decision | Reason | Affects |
|---|---|---|
| **Built a second corpus from Synthea + Faker, as M1 section 8.3 planned**, and kept the in-house one | The project owner asked for both, stored separately, so they can be compared. Synthea (`d9d07a6`, seed 13, 5 years of history) supplies patients, encounters, diagnoses, procedures, costs, labs and medicines. Faker supplies phones, emails, member IDs, MRNs, account numbers and relatives. Both corpora share layouts, noise, warning-sign injection and splits, so they differ only in their facts. | `data/corpus_synthea/`, [realism_comparison.md](realism_comparison.md) |
| Synthea episodes = encounters with a disorder/finding reason and at least one procedure; 1-3 per patient with distinct reasons | Claims need a diagnosis and billable services; distinct reasons avoid 30 near-identical dialysis visits per patient | Synthea diagnosis mix is still skewed (gingivitis 37%) |
| Only inpatient encounters count as stays | Synthea ambulatory visits that cross midnight would otherwise produce one-day "stays" and discharge summaries | Discharge summaries are rare in the Synthea corpus |
| SNOMED CT codes are printed as SNOMED CT, not ICD-10/CPT | Synthea codes are SNOMED; mislabelling them would teach the wrong thing | Layout text only |
| Reference ranges added for the 30 most common Synthea lab tests | Real lab reports always print a range | Lab reports |
| Real Tesseract OCR sets (150 golden docs per corpus) | Tesseract and Pillow are now installed in `.venv` | `real_ocr.jsonl` in each corpus folder; scan images are not committed |
| Raw Synthea output and jar are not committed (`tools/` is ignored) | About 760 MB. The run is reproducible with the command in `scripts/generate_synthea_corpus.py` plus `-r 20261017` to fix Synthea's reference date | Repository size |
