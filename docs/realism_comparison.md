# How real is each synthetic corpus?

Two corpora are built with the same six document types, layouts, noise, injected warning signs and splits. They differ only in where the facts come from:

| | In-house generator | Synthea + Faker |
|---|---|---|
| Folder | `data/corpus/` | `data/corpus_synthea/` |
| Built by | `scripts/generate_corpus.py` | `scripts/generate_synthea_corpus.py` |
| Patients and care | Random draws from hand-written lists (`patients.py`) | Synthea simulated lives (version `d9d07a6`, seed 13, Massachusetts, 5 years of history) |
| Phone, email, member ID, MRN, account | Hand-made formats in never-issued ranges | Faker `en_US` |
| Size | 1,100 patients, 6,802 documents | 1,096 patients, 5,105 documents |
| Real-scan OCR set | `real_ocr.jsonl`, 150 docs | `real_ocr.jsonl`, 150 docs |

This report does not ask how similar the two are to each other. It checks each against outside reference figures and clinical common sense. All numbers come from `scripts/compare_realism.py`, and the raw output is in `reports/realism_stats.json`. Documents with a deliberately injected warning sign are left out of the plausibility checks.

## Scorecard

| Check | Real-world reference | In-house | Synthea + Faker | More realistic |
|---|---|---|---|---|
| Age mix (0-17 / 18-64 / 65+) | 22.1% / 61.1% / 16.8% (2020 Census) | 0% / 64% / 36% | 18% / 64% / 17% | **Synthea** |
| Distance from Census age mix (0 = identical) | 0 | 0.22 | 0.04 | **Synthea** |
| Deliveries/pregnancies outside age 12-55 | 0 | 29 of 56 | 0 of 91 | **Synthea** |
| Deliveries/pregnancies on male-only first names | about 0 | 25 of 56 | 4 of 91 | **Synthea** |
| Children with adult-only diagnoses (heart attack, COPD, ...) | about 0 | no children at all | 1 of 158 | **Synthea** |
| HbA1c in diabetic episodes vs others | clearly higher in diabetics | not higher (median 5.18 vs 5.25) | not measurable (no diabetic episodes sampled) | Neither shown |
| Episodes that include a hospital stay | small minority of care | 43% | 2.5% | **Synthea** |
| Mean length of stay | 4.5 days (HCUP, all US stays) | 6.4 days | 5.2 days | **Synthea** |
| Bill per stay (median) | about $10,400 mean cost (HCUP; charges run higher) | $30,388 | $8,154 | **Synthea** (in-house looks like charges) |
| Diagnosis mix shape | long-tailed: a few conditions dominate | almost uniform (evenness 0.99, top 5 = 11%) | long-tailed (evenness 0.66, top 5 = 63%) | **Synthea** for shape |
| Most common diagnosis | (none) | spread evenly over 20 codes | gingivitis, 37% of episodes | **In-house** (Synthea's content is skewed) |
| Distinct procedures / medicines / lab tests / providers | far more than either | 26 / 21 / 16 / 11 | 148 / 106 / 86 / 201 | **Synthea** |
| Surnames in the US census-based list (Faker `en_US`) | high | 76% | 21% | **In-house** |
| Patients sharing a full name with another patient | very rare | 21% | 0% | **Synthea** |
| Phone numbers in the fictional 555 range | 0% | 100% | 7% | **Synthea** |
| Real email providers (gmail, yahoo, ...) | yes | no, reserved test domains only | yes | **Synthea** |
| ZIP matches state | 100% | 100% | 100% | Tie |
| Geographic spread | 50 states | 18 cities in 18 states | 258 towns, one state (MA) | **In-house** for spread, Synthea for realism |
| Multimorbidity rising with age | strongly rising | flat (1.41 / 1.41 / 1.43) | flat (1.27 / 1.31 / 1.35) | Neither (we only sample 1-3 episodes) |
| Real Tesseract OCR: PII strings surviving verbatim | (none) | 86.4% | 86.5% | Tie (same layouts) |

## What this means

**Synthea + Faker is more realistic on most checks.** Its patients have a census-like age mix, including children. Its diagnoses fit the patient's age and sex. Stays, length of stay and costs are close to national figures, and its clinical vocabulary is five to ten times richer. The in-house generator fails basic clinical sense: half of its deliveries are for patients over 55 or with male names, it has no children, and its labs ignore the diagnosis.

**The in-house generator is better on a few points:**
- **Common names.** Synthea draws names from a generator list ("Lebsack", "Cruickshank", "O'Kon") rather than common US surnames.
- **Balanced diagnoses and many stays.** This is unrealistic, but it gives a model enough examples of every case. In Synthea, gingivitis is 37% of episodes and only 35 bills cover a hospital stay, so it has few discharge summaries and high-value stays to learn from.
- **Geographic spread.** All Synthea addresses are in Massachusetts.
- **Safety for publishing.** Every phone and email is in a reserved fictional range. Faker phone numbers and `name@gmail.com` addresses look real and could, by chance, belong to real people.

**What both share:** layouts, noise, the injected warning signs and the amount scaling for routing ambiguity all come from our own code. The amount scaling pushes 22% of episodes into the $19k-$31k band whatever the care was. In the Synthea corpus this produces bills like a routine dental cleaning claimed at $21,843. The in-house corpus has the same effect on cheap procedures. Text-level realism therefore differs only in the facts filled into the templates.

## Recommendation

1. Use **Synthea + Faker as the main realism source**, but fix its skew before training. Cap any single diagnosis at about 10% of episodes, and oversample inpatient encounters so discharge summaries and high-value stays have enough examples.
2. Replace Synthea's generator-style surnames with Faker `en_US` names, and keep Faker identifiers out of the published corpus or move them into reserved ranges.
3. Keep the in-house corpus as a balanced, privacy-safe control set.
4. Settle "which is the better dataset" in M3 by training the same baselines on each and scoring both on both test sets, plus the real-OCR sets. Realism and usefulness for training are different questions.

## Sources

- 2020 Census age figures: [US Census Bureau, 2020 Census Demographic Profile release](https://census.gov/newsroom/press-releases/2023/2020-census-demographic-profile-and-dhc.html)
- Length of stay and cost per stay (2012, all US stays): [HCUP Statistical Brief #180](https://hcup-us.ahrq.gov/reports/statbriefs/sb180-Hospitalizations-United-States-2012.jsp). This is the most recent all-stays brief the search returned. HCUP reports costs, which are lower than the charges printed on bills.
- Synthea: [synthetichealth/synthea](https://github.com/synthetichealth/synthea), run metadata in `data/corpus_synthea/synthea_run.json`
- Name reference lists: Faker `en_US` person provider (v40.43.0)
