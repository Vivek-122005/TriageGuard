# How real is each synthetic corpus?

Two corpora are built with the same six document types, layouts, noise, injected warning signs and splits. They differ only in where the facts come from:

| | In-house generator | Synthea + Faker |
|---|---|---|
| Folder | `data/corpus/` | `data/corpus_synthea/` |
| Built by | `scripts/generate_corpus.py` | `scripts/generate_synthea_corpus.py` |
| Patients and care | Random draws from hand-written lists (`patients.py`) | Synthea simulated lives (version `d9d07a6`, seed 13, reference date 2026-10-17, 3,474 simulated (3,000 alive at the reference date), Massachusetts, 5 years of history) |
| Names, phone, email, member ID, MRN, account | Hand-made formats in never-issued ranges | Faker `en_US` names by sex; phones in the fictional 555-01xx block; reserved email domains |
| Sampling | All patients | 1,100 patients: 40% who had a hospital stay, any diagnosis capped at about 10% of episodes |
| Size | 1,100 patients, 6,802 documents | 1,100 patients, 5,591 documents (corpus version `m2-synthea-v2`) |
| Real-scan OCR set | `real_ocr.jsonl`, 150 docs | `real_ocr.jsonl`, 150 docs |

This report does not ask how similar the two are to each other. It checks each against outside reference figures and clinical common sense. All numbers come from `scripts/compare_realism.py`, and the raw output is in `reports/realism_stats.json`. Documents with a deliberately injected warning sign are left out of the plausibility checks.

## Scorecard (Synthea corpus v2, after rebalancing)

| Check | Real-world reference | In-house | Synthea + Faker v2 | More realistic |
|---|---|---|---|---|
| Age mix (0-17 / 18-64 / 65+) | 22.1% / 61.1% / 16.8% (2020 Census) | 0% / 64% / 36% | 14% / 64% / 22% | **Synthea** |
| Distance from Census age mix (0 = identical) | 0 | 0.22 | 0.08 | **Synthea** |
| Deliveries/pregnancies outside age 12-55 | 0 | 29 of 56 | 0 of 82 | **Synthea** |
| Deliveries/pregnancies on male-only first names | 0 | 25 of 56 | 0 of 82 | **Synthea** |
| Children with adult-only diagnoses | about 0 | no children at all | 1 of 138 | **Synthea** |
| HbA1c higher in diabetic episodes | yes | no (median 5.18 vs 5.25) | not measurable (no diabetic episodes sampled) | Neither shown |
| Mean length of stay | 4.5 days (HCUP) | 6.4 days | 3.7 days | **Synthea** (closer) |
| Bill per stay (median) | about $10,400 mean cost (HCUP; charges run higher) | $30,388 | $9,037 | **Synthea** |
| Diagnosis mix shape | long-tailed | almost uniform (evenness 0.99) | long-tailed but capped (evenness 0.83, top 5 = 35%) | **Synthea** |
| Distinct procedures / medicines / lab tests / providers | far more than either | 26 / 21 / 16 / 11 | 176 / 113 / 80 / 206 | **Synthea** |
| Patients sharing a full name | very rare | 21% | 2% | **Synthea** |
| Names in census-based US lists | high | 52% first / 76% last | 100% (drawn from those lists, so this check is circular now) | Synthea, by construction |
| Phones and emails fictional (safe to publish) | (privacy goal) | 100% | 100% | Tie |
| ZIP matches state | 100% | 100% | 100% | Tie |
| Geographic spread | 50 states | 18 cities in 18 states | 258 towns, one state (MA) | **In-house** for spread |
| Episodes that include a hospital stay | small minority of real care | 43% | 28% (deliberately oversampled) | Neither: both oversample stays for training |
| Multimorbidity rising with age | strongly rising | flat | slightly rising (1.25 / 1.32 / 1.35) | Neither (we sample only 1-3 episodes) |

## What changed from v1 to v2 and why

| | v1 (first Synthea run) | v2 (now) | Why |
|---|---|---|---|
| Synthea run | 1,263 simulated patients, run date not pinned | 3,474 simulated (3,000 alive), reference date pinned (`-r 20261017`) | More stay patients to choose from; reproducible on any day |
| Discharge summaries | 42 in total (3 in golden) | 470 (47 in golden) | 40% of places go to patients who had a stay |
| Most common diagnosis | gingivitis, 37% of episodes | gingivitis, about 11% | Running cap of 10% per diagnosis |
| Distinct diagnoses | 58 | 75 | Cap makes room for rarer conditions |
| Names | Synthea's generator names ("Lebsack", "O'Kon") | Faker `en_US` census-based names, matched to sex | Realism |
| Phones and emails | Real-looking ranges and gmail/yahoo | 555-01xx block and reserved domains | Safe to publish |
| Age distance from Census | 0.04 | 0.08 | Stay patients are older; accepted trade-off |
| Share of episodes with a stay | 2.5% | 28% | Deliberate, so stays and high-value routes are learnable |

## What this means

**Synthea + Faker v2 is the more realistic dataset and is the main one.** Its patients are plausible people: children and seniors in roughly Census proportions, deliveries only for women of child-bearing age, and children without adult-only diseases. Their care is plausible too, with stay lengths and costs near national figures and a vocabulary five to ten times richer. The rebalancing changes only which Synthea patients and encounters are sampled. The clinical facts themselves are untouched.

**What v2 still does not fix:**
- Every address is in Massachusetts.
- Stays are over-represented on purpose, so the share of stays is not realistic.
- High-value documents are still few (39 in golden), because Synthea stays are cheap next to our $25,000 high-value line.
- Layouts, noise, warning-sign injection and amount scaling are our own code in both corpora. The scaling pushes 22% of episodes into the $19k-$31k band whatever the care was, which produces bills like a routine dental cleaning claimed at about $21,800.

The in-house corpus stays as a balanced control set. M3 will train on Synthea v2 and score on both corpora's test sets, which shows how well models trained on one source transfer to the other.

## Sources

- 2020 Census age figures: [US Census Bureau, 2020 Census Demographic Profile release](https://census.gov/newsroom/press-releases/2023/2020-census-demographic-profile-and-dhc.html)
- Length of stay and cost per stay (2012, all US stays): [HCUP Statistical Brief #180](https://hcup-us.ahrq.gov/reports/statbriefs/sb180-Hospitalizations-United-States-2012.jsp). This is the most recent all-stays brief the search returned. HCUP reports costs, which are lower than the charges printed on bills.
- Synthea: [synthetichealth/synthea](https://github.com/synthetichealth/synthea), run metadata in `data/corpus_synthea/synthea_run.json`, run command in `scripts/generate_synthea_corpus.py`
- Name reference lists: Faker `en_US` person provider (v40.43.0)
