"""Document layouts: four per document type (M1 section 8.3, step 3).

Layout index 3 of every type is the held-out layout. It never appears in
train, validation or the golden test set, only in the hard test set, so we can
tell whether a model reads documents or memorises templates (M1 section 8.4).

Each layout writes through a DocBuilder and records two things:
* b.fields: the ground-truth key fields for the document type, normalised
  (ISO dates, float amounts). A field dropped by missing-field noise is None.
* shown: the facts that are actually visible in the text. Routing labels are
  computed only from these, so a label is always recoverable from the text.
"""

from __future__ import annotations

import random

from .builder import DocBuilder
from .patients import Episode

HELD_OUT_LAYOUT = 3


def _shown() -> dict:
    return {"dob": None, "service_dates": [], "admission": None, "discharge": None,
            "amount": None, "diag_family": None, "proc_families": [], "line_items": []}


def _doc_name(ep: Episode) -> str:
    return f"{ep.doctor_first} {ep.doctor_last}"


# ---------------------------------------------------------------- patient blocks
def _patient_block(b: DocBuilder, ep: Episode, s: dict, variant: int) -> None:
    p = ep.patient
    s["dob"] = p.dob
    if variant == 0:
        b.lit("Patient: ").pii("NAME", b.name(p.first, p.last)).lit("   DOB: ").pii("DATE_OF_BIRTH", b.date_(p.dob))
        b.lit("   SSN: ").pii("SSN", b.ssn(p.ssn)).nl()
        b.lit("Phone: ").pii("PHONE", b.phone(p.phone)).lit("   Member ID: ").pii("MEMBER_ID", b.member_id(p.member_id)).nl()
        if b.keep():
            b.lit("Address: ").pii("ADDRESS", p.address).nl()
    elif variant == 1:
        b.lit("PATIENT INFORMATION\n")
        b.lit("Name ........ ").pii("NAME", b.name(p.first, p.last)).nl()
        b.lit("Date of Birth ").pii("DATE_OF_BIRTH", b.date_(p.dob)).nl()
        b.lit("Medical Record Number: ").pii("MRN", b.mrn(p.mrn)).nl()
        b.lit("Insurance member no.: ").pii("MEMBER_ID", b.member_id(p.member_id)).nl()
        if b.keep():
            b.lit("Telephone: ").pii("PHONE", b.phone(p.phone)).lit(" | Email: ").pii("EMAIL", p.email).nl()
    elif variant == 2:
        b.lit("Insured: ").pii("NAME", b.name(p.first, p.last)).lit(", born ").pii("DATE_OF_BIRTH", b.date_(p.dob))
        b.lit(", residing at ").pii("ADDRESS", p.address).lit(".\n")
        b.lit("Policy/Member: ").pii("MEMBER_ID", b.member_id(p.member_id)).lit("  Account: ").pii("ACCOUNT_NUMBER", b.account(p.account_number)).nl()
    else:
        # Held-out style: single-line pipe-separated header.
        b.lit("PT ").pii("NAME", b.name(p.first, p.last)).lit(" | DOB ").pii("DATE_OF_BIRTH", b.date_(p.dob))
        b.lit(" | MRN ").pii("MRN", b.mrn(p.mrn)).lit(" | SSN ").pii("SSN", b.ssn(p.ssn)).lit(" | Contact ").pii("PHONE", b.phone(p.phone)).nl()


# ---------------------------------------------------------------- claim form
def claim_form(b: DocBuilder, ep: Episode, layout: int) -> dict:
    s = _shown()
    titles = ["HEALTH INSURANCE CLAIM FORM", "Member Reimbursement Claim", "CLAIM SUBMISSION - PROFESSIONAL SERVICES", "Claim for Benefits (Form CB-7)"]
    b.lit(titles[layout] + "\n")
    b.lit(f"Insurer: {ep.insurer}    Claim Number: {ep.claim_number}\n\n")
    _patient_block(b, ep, s, layout)
    b.nl()
    s["service_dates"].append(ep.admission)
    procs = []
    dropped = []
    b.fields["diagnosis"] = None
    if layout in (0, 1):
        b.lit("Diagnosis: ").field("diagnosis", ep.diag_text).lit(f" ({ep.code_system} {ep.diag_code})\n")
        b.fields["diagnosis"] = ep.diag_text
        s["diag_family"] = ep.diag_family
        b.lit("Date of service: ").field("service_date", b.date_(ep.admission)).nl()
        if b.keep():
            b.lit("Rendering provider: ").field("provider", ep.provider).nl()
        else:
            dropped.append("provider")
        b.lit("\nServices:\n")
    elif layout == 2:
        b.lit("Section B - Treatment\n")
        b.lit("The member was treated at ").field("provider", ep.provider).lit(" on ").field("service_date", b.date_(ep.admission))
        b.lit(" for ").field("diagnosis", ep.diag_text).lit(".\n")
        b.fields["diagnosis"] = ep.diag_text
        s["diag_family"] = ep.diag_family
        b.lit("Itemised services:\n")
    else:
        b.lit(f"Dx code {ep.diag_code}: ").field("diagnosis", ep.diag_text).lit("\n")
        b.fields["diagnosis"] = ep.diag_text
        s["diag_family"] = ep.diag_family
        b.lit("Facility: ").field("provider", ep.provider).lit(" / DOS ").field("service_date", b.date_(ep.admission)).nl()
        b.lit("Lines:\n")
    proc_names = {p[0]: p for p in ep.procedures}
    k = 0
    for li in ep.line_items:
        if li.description in proc_names:
            fam = proc_names[li.description][2]
            s["proc_families"].append(fam)
            b.lit(f"  {k + 1}. ").field("procedure", li.description, item=len(procs)).lit(f"  [{li.code}]  {b.money(li.amount)}\n")
            procs.append(li.description)
            s["line_items"].append((li.description, li.amount))
            k += 1
    other = round(ep.total - sum(a for _, a in s["line_items"]), 2)
    if other > 0:
        b.lit(f"  {k + 1}. Facility and ancillary charges  {b.money(other)}\n")
    b.nl()
    total_labels = ["Total amount claimed: ", "Amount claimed: ", "TOTAL CLAIMED ", "Sum requested = "]
    b.lit(total_labels[layout]).field("claimed_amount", b.money(ep.total)).nl()
    s["amount"] = ep.total
    b.lit("\nI certify that the information above is true and complete.\n")
    if layout == 1 and b.keep():
        b.lit("Signed: ").pii("NAME", b.name(ep.patient.first, ep.patient.last)).nl()
    b.fields.update({"claimed_amount": ep.total, "procedure": procs, "service_date": ep.admission.isoformat(), "provider": ep.provider})
    for f in dropped:
        b.fields[f] = None
    return s


# ---------------------------------------------------------------- hospital bill
def hospital_bill(b: DocBuilder, ep: Episode, layout: int) -> dict:
    s = _shown()
    b.lit([f"{ep.provider.upper()}\nPATIENT STATEMENT\n", f"{ep.provider}\nItemized Hospital Bill\n",
           f"INVOICE - {ep.provider}\n", f"{ep.provider} :: billing summary\n"][layout])
    b.lit("Statement date: " + b.date_(ep.prescription_date) + "\n")
    if layout == 2:
        b.lit("Account Number: ").pii("ACCOUNT_NUMBER", b.account(ep.patient.account_number)).nl()
    _patient_block(b, ep, s, layout if layout != 2 else 0)
    b.nl()
    b.fields["admission_date"] = b.fields["discharge_date"] = None
    adm_lbl, dis_lbl = [("Admitted: ", "   Discharged: "), ("Admission Date: ", "\nDischarge Date: "),
                        ("Stay from ", " to "), ("ADM ", " / DC ")][layout]
    b.lit(adm_lbl).field("admission_date", b.date_(ep.admission)).lit(dis_lbl).field("discharge_date", b.date_(ep.discharge)).nl()
    b.fields["admission_date"], b.fields["discharge_date"] = ep.admission.isoformat(), ep.discharge.isoformat()
    s["admission"], s["discharge"] = ep.admission, ep.discharge
    s["service_dates"] += [ep.admission, ep.discharge]
    if layout in (0, 3) or b.rng.random() < 0.4:
        b.lit("Diagnosis: " + ep.diag_text + "\n")
        s["diag_family"] = ep.diag_family
    b.lit(["\nCHARGES\n", "\nDescription                         Code     Amount\n", "\nItem | Code | Charge\n", "\n-- lines --\n"][layout])
    items = []
    proc_fam = {p[0]: p[2] for p in ep.procedures}
    for i, li in enumerate(ep.line_items):
        if li.description in proc_fam:
            s["proc_families"].append(proc_fam[li.description])
        s["line_items"].append((li.description, li.amount))
        if layout == 2:
            b.field("line_items", li.description, part="description", item=i).lit(f" | {li.code} | ").field("line_items", b.money(li.amount), part="amount", item=i).nl()
        else:
            b.lit("  ").field("line_items", li.description, part="description", item=i).lit(f"   {li.code}   ").field("line_items", b.money(li.amount), part="amount", item=i).nl()
        items.append({"description": li.description, "amount": li.amount})
    b.lit(["\nTotal billed: ", "\nTOTAL CHARGES: ", "\nAmount due: ", "\nGRAND TOTAL "][layout]).field("total_billed", b.money(ep.total)).nl()
    s["amount"] = ep.total
    if layout == 1 and b.keep():
        b.lit("Questions? Call billing at 1-800-555-0199 and quote MRN ").pii("MRN", b.mrn(ep.patient.mrn)).lit(".\n")
    b.fields.update({"total_billed": ep.total, "line_items": items})
    return s


# ---------------------------------------------------------------- discharge summary
_COURSE = [
    "The patient presented with symptoms consistent with {dx} and was admitted for further management.",
    "{name} was admitted after evaluation in the emergency department confirmed {dx}.",
    "Admitted with a working diagnosis of {dx}; workup supported this.",
    "Patient is a {age}-year-old who came in with worsening symptoms and was found to have {dx}.",
]
_OUTCOME = [
    "Recovery was uneventful and the patient was discharged in stable condition.",
    "The hospital course was complicated by mild post-procedure pain, managed conservatively.",
    "Vital signs remained stable and the patient tolerated a regular diet before discharge.",
    "Patient improved steadily and was ambulating independently at discharge.",
]


def discharge_summary(b: DocBuilder, ep: Episode, layout: int) -> dict:
    s = _shown()
    p = ep.patient
    b.lit(["DISCHARGE SUMMARY\n", f"{ep.provider}\nDischarge Summary\n", "Hospital Discharge Note\n", "D/C SUMMARY -- INPATIENT\n"][layout])
    _patient_block(b, ep, s, layout)
    b.lit("Attending physician: ").field("doctor", b.doctor(ep.doctor_first, ep.doctor_last), pii_label="NAME").nl()
    b.lit("Admission Date: ").field("admission_date", b.date_(ep.admission)).lit("\nDischarge Date: ").field("discharge_date", b.date_(ep.discharge)).nl(2)
    s["admission"], s["discharge"] = ep.admission, ep.discharge
    s["service_dates"] += [ep.admission, ep.discharge]
    s["diag_family"] = ep.diag_family
    procs = []
    if layout in (0, 1):
        b.lit("Principal Diagnosis: ").field("diagnosis", ep.diag_text).lit(f" ({ep.diag_code})\n")
        b.lit("Procedures performed:\n")
        for i, (name, code, fam) in enumerate(ep.procedures):
            b.lit("- ").field("procedures", name, item=i).lit(f" ({code})\n")
            procs.append(name)
            s["proc_families"].append(fam)
        b.lit("\nHospital Course:\n")
        age = max(0, ep.admission.year - p.dob.year)
        course = b.rng.choice(_COURSE).replace("{age}", str(age))
        pre, _, post = course.partition("{dx}")
        if "{name}" in pre:
            a, _, c = pre.partition("{name}")
            b.lit(a).pii("NAME", b.name(p.first, p.last)).lit(c)
        else:
            b.lit(pre)
        b.lit(ep.diag_text + post + " ")
    else:
        b.lit("Assessment: the patient was treated for ").field("diagnosis", ep.diag_text).lit(". ")
        b.lit("During the stay the following were done: ")
        for i, (name, code, fam) in enumerate(ep.procedures):
            if i:
                b.lit(", " if i < len(ep.procedures) - 1 else " and ")
            b.field("procedures", name, item=i)
            procs.append(name)
            s["proc_families"].append(fam)
        b.lit(". ")
    b.lit(b.rng.choice(_OUTCOME) + "\n")
    if b.keep():
        b.lit("\nFamily contact: ").pii("NAME", f"{p.relative_first} {p.relative_last}").lit(f" ({p.relative_relation}), reachable at ")
        b.pii("PHONE", b.phone(p.relative_phone)).lit(".\n")
    b.lit("\nDischarge medications:\n")
    for name, strength, freq, dur in ep.meds:
        b.lit(f"  {name} {strength} {freq} for {dur}\n")
    b.lit("\nFollow up with ").lit(ep.provider).lit(" in two weeks.\n")
    b.lit("Electronically signed by ").pii("NAME", b.doctor(ep.doctor_first, ep.doctor_last)).nl()
    b.fields.update({"diagnosis": ep.diag_text, "procedures": procs, "admission_date": ep.admission.isoformat(),
                     "discharge_date": ep.discharge.isoformat(), "doctor": _doc_name(ep)})
    return s


# ---------------------------------------------------------------- lab report
def lab_report(b: DocBuilder, ep: Episode, layout: int) -> dict:
    s = _shown()
    b.lit([f"{ep.lab}\nLABORATORY REPORT\n", f"{ep.lab} - Clinical Chemistry Results\n", "LAB RESULTS\n", f"[{ep.lab}] result printout\n"][layout])
    _patient_block(b, ep, s, layout)
    if b.keep():
        b.lit("Ordering physician: ").pii("NAME", b.doctor(ep.doctor_first, ep.doctor_last)).nl()
    b.lit(["Collected: ", "Specimen collection date: ", "Sample drawn on ", "COLL DT "][layout]).field("collection_date", b.date_(ep.collection_date)).nl(2)
    s["service_dates"].append(ep.collection_date)
    tests = []
    if layout == 1:
        b.lit("Test                      Result     Units        Reference\n")
    for i, (test, val, unit, lo, hi) in enumerate(ep.labs):
        flag = " H" if hi is not None and val > hi else ""
        ref = f"{lo}-{hi}" if lo is not None else "n/a"
        ref_wide = f"{lo} - {hi}" if lo is not None else "n/a"
        if layout == 2:
            b.lit("- ").field("tests", test, part="name", item=i).lit(" came back at ").field("tests", f"{val}", part="value", item=i).lit(f" {unit} (normal {ref}){flag}.\n")
        elif layout == 3:
            b.field("tests", test, part="name", item=i).lit("=").field("tests", f"{val}", part="value", item=i).lit(f"{unit};ref {ref}{flag}\n")
        else:
            b.field("tests", test, part="name", item=i).lit("   ").field("tests", f"{val}", part="value", item=i).lit(f"   {unit}   {ref_wide}{flag}\n")
        tests.append({"name": test, "value": val, "unit": unit})
    b.lit("\nResults verified by laboratory staff.\n")
    b.fields.update({"tests": tests, "collection_date": ep.collection_date.isoformat()})
    return s


# ---------------------------------------------------------------- prescription
def prescription(b: DocBuilder, ep: Episode, layout: int) -> dict:
    s = _shown()
    b.lit([f"{ep.provider}\nPRESCRIPTION\n", "Rx\n", f"Outpatient Prescription - {ep.provider}\n", "e-Rx transmission\n"][layout])
    b.lit("Date: ").field("prescription_date", b.date_(ep.prescription_date)).nl()
    s["service_dates"].append(ep.prescription_date)
    _patient_block(b, ep, s, layout)
    b.nl()
    meds = []
    for i, (name, strength, freq, dur) in enumerate(ep.meds):
        if layout == 3:
            b.lit(f"#{i + 1} ").field("medicines", name, part="name", item=i).lit(" ").field("medicines", strength, part="dose", item=i).lit(f" sig: {freq} x {dur}\n")
        elif layout == 2:
            b.lit("Take ").field("medicines", name, part="name", item=i).lit(", ").field("medicines", strength, part="dose", item=i).lit(f", {freq} for {dur}.\n")
        else:
            b.lit(f"{i + 1}) ").field("medicines", name, part="name", item=i).lit("  ").field("medicines", strength, part="dose", item=i).lit(f"  {freq}  Qty: {dur}\n")
        meds.append({"name": name, "dose": strength})
    b.lit(f"\nDispense at: {ep.pharmacy}\n")
    b.lit("Prescriber: ").field("doctor", b.doctor(ep.doctor_first, ep.doctor_last), pii_label="NAME").nl()
    if layout == 0 and b.keep():
        b.lit("Prescriber phone: ").pii("PHONE", b.phone("555" + ep.patient.phone[3:6][::-1] + ep.patient.phone[6:][::-1])).nl()
    b.fields.update({"medicines": meds, "doctor": _doc_name(ep), "prescription_date": ep.prescription_date.isoformat()})
    return s


# ---------------------------------------------------------------- pre-authorization letter
def preauth_letter(b: DocBuilder, ep: Episode, layout: int) -> dict:
    s = _shown()
    p = ep.patient
    proc_name, proc_code, proc_fam = ep.procedures[0]
    est = round(sum(li.amount for li in ep.line_items if li.description == proc_name) * b.rng.uniform(1.0, 1.25), 2)
    s["proc_families"].append(proc_fam)
    s["diag_family"] = ep.diag_family
    s["amount"] = est
    b.lit([f"{ep.provider}\n", f"{ep.insurer} - Utilization Review\n", "REQUEST FOR PRIOR AUTHORIZATION\n", "PA REQ\n"][layout])
    b.lit("Date: " + b.date_(ep.letter_date) + "\n\n")
    s["service_dates"].append(ep.letter_date)
    if layout == 0:
        b.lit(f"To: {ep.insurer}, Prior Authorization Department\n\n")
        b.lit("Re: ").pii("NAME", b.name(p.first, p.last)).lit(", Member ID ").pii("MEMBER_ID", b.member_id(p.member_id)).lit(", DOB ").pii("DATE_OF_BIRTH", b.date_(p.dob)).nl(2)
        s["dob"] = p.dob
        b.lit("Dear Reviewer,\n\nI am writing to request pre-authorization for ").field("requested_procedure", proc_name)
        b.lit(f" ({ep.proc_code_system} {proc_code}) for my patient, who has been diagnosed with ").field("diagnosis", ep.diag_text)
        b.lit(". Conservative management has not been sufficient. The estimated cost of the procedure is ").field("estimated_cost", b.money(est)).lit(".\n\n")
        b.lit("Please contact my office with any questions.\n\nSincerely,\n").pii("NAME", b.doctor(ep.doctor_first, ep.doctor_last)).nl()
    else:
        _patient_block(b, ep, s, layout)
        b.nl()
        b.lit(["Requested procedure: ", "Service requested: ", "Proc: "][layout - 1]).field("requested_procedure", proc_name).lit(f" ({proc_code})\n")
        b.lit(["Diagnosis: ", "Clinical indication: ", "Dx: "][layout - 1]).field("diagnosis", ep.diag_text).nl()
        b.lit(["Estimated cost: ", "Estimated charges: ", "Est. $ "][layout - 1]).field("estimated_cost", b.money(est)).nl()
        b.lit("Requesting physician: ").pii("NAME", b.doctor(ep.doctor_first, ep.doctor_last)).nl()
        if b.keep():
            b.lit("Planned date: ").lit(b.date_(ep.admission)).nl()
            s["service_dates"].append(ep.admission)
    b.fields.update({"requested_procedure": proc_name, "diagnosis": ep.diag_text, "estimated_cost": est})
    return s


RENDERERS = {
    "claim_form": claim_form,
    "hospital_bill": hospital_bill,
    "discharge_summary": discharge_summary,
    "lab_report": lab_report,
    "prescription": prescription,
    "preauth_letter": preauth_letter,
}


def render(doc_type: str, b: DocBuilder, ep: Episode, layout: int) -> dict:
    return RENDERERS[doc_type](b, ep, layout)


def doc_types_for_episode(rng: random.Random, ep: Episode) -> list[str]:
    """Which documents an episode produces. Inpatient stays get a summary."""
    types = ["claim_form", "hospital_bill"]
    if ep.length_of_stay != 0:
        types.append("discharge_summary")
    if rng.random() < 0.75 and ep.labs:
        types.append("lab_report")
    if rng.random() < 0.7 and ep.meds:
        types.append("prescription")
    if rng.random() < 0.45:
        types.append("preauth_letter")
    return types
