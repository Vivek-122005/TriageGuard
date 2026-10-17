"""Shared label sets for every TriageGuard stage.

Keeping these in one place means the data generator, the models and the API
all agree on spelling. The PII list is a setting (M1 section 10): a new
identifier pack (for example Aadhaar/PAN for India) is added here.
"""

# Tier 1 direct identifiers: always masked in the safe copy.
PII_LABELS = [
    "NAME",
    "DATE_OF_BIRTH",
    "SSN",
    "PHONE",
    "EMAIL",
    "ADDRESS",
    "MEMBER_ID",
    "MRN",
    "ACCOUNT_NUMBER",
]

DOC_TYPES = [
    "claim_form",
    "hospital_bill",
    "discharge_summary",
    "lab_report",
    "prescription",
    "preauth_letter",
]

# Key fields per document type (M1 section 4.4).
FIELDS_BY_TYPE = {
    "claim_form": ["claimed_amount", "diagnosis", "procedure", "service_date", "provider"],
    "hospital_bill": ["total_billed", "line_items", "admission_date", "discharge_date"],
    "discharge_summary": ["diagnosis", "procedures", "admission_date", "discharge_date", "doctor"],
    "lab_report": ["tests", "collection_date"],
    "prescription": ["medicines", "doctor", "prescription_date"],
    "preauth_letter": ["requested_procedure", "diagnosis", "estimated_cost"],
}

ROUTES = ["routine", "high_value", "suspicious"]

# Warning signs injected into the synthetic data. "Suspicious" is not "fraud":
# we have no real fraud labels (M1 section 4.5).
SUSPICIOUS_SIGNALS = ["duplicate_billing", "impossible_dates", "procedure_mismatch"]

SPLITS = ["train", "val", "test_golden", "test_hard"]
