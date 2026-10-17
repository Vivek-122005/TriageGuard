# Privacy notes (M2)

## What counts as private

We use HIPAA's 18 Safe Harbor identifiers as design guidance, not as a compliance claim (M1 section 10). The corpus labels the nine that occur in claim paperwork. They are the Tier 1 direct identifiers and are always masked in the safe copy.

| Label | Examples in the corpus | HIPAA identifier |
|---|---|---|
| NAME | patient, relative, doctors (`RIVERA, JANE`, `Dr. T. King`) | names |
| DATE_OF_BIRTH | `03/31/1983`, `31-Mar-1983` | dates directly related to an individual |
| SSN | `926-69-0768`, `926 69 0768` | social security numbers |
| PHONE | `(555) 680-0544` | telephone numbers |
| EMAIL | `gloria.kowalski79@example.com` | email addresses |
| ADDRESS | `6968 Pine Dr, Bristol, CT 06004` | geographic subdivisions smaller than a state |
| MEMBER_ID | `MB-3318702` | health plan beneficiary numbers |
| MRN | `MRN77300120` | medical record numbers |
| ACCOUNT_NUMBER | `AC824409771` | account numbers |

The list is the `PII_LABELS` setting in `triageguard/schema.py`. A country pack (for example Aadhaar and PAN for India) is added there plus patterns in the redactor.

## Tier 2 working facts

Service dates, amounts, diagnosis and procedure names, and provider organisations are not masked, because field extraction and routing need them. They stay inside the protected area. Anything that leaves it (logs, dashboards, exports) generalises them, for example dates to month and amounts to bands.

## Decisions made while building the data

* **Doctor names are both a field and PII.** M1 lists "doctor" as a field for discharge summaries and prescriptions and also lists doctors' names as PII. The corpus labels the span twice: as a `NAME` PII span and as a `doctor` field span. The pipeline extracts the doctor field from the raw text inside the protected area. The safe copy and anything logged show `[NAME]`.
* **Date of birth feeds a routing rule.** "Service before birth" is an impossible-dates signal, so routing runs on the raw text inside the protected area, not on the safe copy. The routing output only carries the signal name, never the date.
* **Relatives are PII too.** Discharge summaries name a family contact with their own phone number. Both are labelled.
* **Organisations are not PII.** Hospitals, labs, pharmacies and insurers are labelled as fields where relevant, never masked.

## Why the corpus is safe to publish

* Every person is generated. Names are drawn from small generic lists and combined at random.
* SSNs use area numbers 900-999, which the Social Security Administration never issues. `validate.py` fails generation if a clean document contains an SSN outside this range.
* Phone numbers use the 555 exchange. Email domains are `example.com`, `example.org`, `example.net` and `.test`, all reserved for documentation.
* No real clinical text was copied in. Narrative sentences are hand-written templates.

## Rules for later milestones

1. Logs, stored outputs and reviewer screens use the safe copy only. Raw text is never logged.
2. The redactor is scored recall-first. A missed identifier is a leak, so per-label entity recall is reported, plus a strict "any character of the identifier left unmasked" leak count.
3. On real OCR output, where spans do not align, leakage is measured by searching the redacted text for each original identifier and for its digit sequence.
4. Reviewer corrections that become training data go through the redactor first.

## The Synthea + Faker corpus

* Synthea patients are simulated, and Synthea SSNs use the never-issued 999 area.
* Faker phone numbers are in real number ranges, and its emails use real providers (`gmail.com`, `yahoo.com`, `hotmail.com`). A generated `firstname.lastname@gmail.com` or phone number could belong to a real person by chance. The values are not linked to any real person's data, but before this corpus is published more widely, its phones should be moved into the 555 range and its emails onto reserved domains. Its realism comes from the clinical facts, not from these contact details.
* Synthea addresses use real Massachusetts town names and ZIP codes with invented street names and numbers.
