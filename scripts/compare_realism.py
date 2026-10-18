"""How realistic is each synthetic corpus? (in-house generator vs Synthea + Faker)

This does not ask how similar the two corpora are to each other. It checks
each one against outside reference points and clinical common sense:

A. demographics: age mix vs the 2020 US Census, name realism
B. clinical plausibility: age/sex-impossible diagnoses, lab values that fit
   the diagnosis, multimorbidity rising with age
C. utilisation and cost: length of stay and cost per stay vs HCUP,
   long-tailed diagnosis mix
D. surface realism: identifier formats, ZIP/state consistency, vocabulary

Documents carrying an injected warning sign are excluded from the
plausibility checks, because those errors are deliberate.

Writes docs/realism_comparison.md and reports/realism_stats.json.
Usage: .venv/bin/python scripts/compare_realism.py
"""

import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from faker.providers.person.en_US import Provider as USNames  # noqa: E402

CORPORA = {"in-house": ROOT / "data" / "corpus", "synthea+faker": ROOT / "data" / "corpus_synthea"}
SPLITS = ["train", "val", "test_golden", "test_hard"]

# Reference points (see the sources list at the end of the report).
CENSUS_AGE = {"0-17": 0.221, "18-64": 0.611, "65+": 0.168}
HCUP_LOS_DAYS = 4.5
HCUP_COST_PER_STAY = 10_400

FIRST_NAMES = {n.lower() for n in USNames.first_names}
MALE_ONLY = {n.lower() for n in USNames.first_names_male} - {n.lower() for n in USNames.first_names_female}
FEMALE_ONLY = {n.lower() for n in USNames.first_names_female} - {n.lower() for n in USNames.first_names_male}
LAST_NAMES = {n.lower() for n in USNames.last_names}

ZIP_REGION = {"0": "CT MA ME NH NJ PR RI VT", "1": "DE NY PA", "2": "DC MD NC SC VA WV", "3": "AL FL GA MS TN",
              "4": "IN KY MI OH", "5": "IA MN MT ND SD WI", "6": "IL KS MO NE", "7": "AR LA OK TX",
              "8": "AZ CO ID NM NV UT WY", "9": "AK CA HI OR WA"}

OBSTETRIC = re.compile(r"pregnan|deliver|labor|prenatal|obstetric", re.I)
ADULT_ONLY = re.compile(r"osteoarthritis|myocardial infarction|NSTEMI|heart failure|CHF|COPD|chronic obstructive|"
                        r"atrial fibrillation|AFib|ischemic heart|knee replacement|hip fracture|femoral neck|"
                        r"dementia|Alzheimer|prostate|end-stage renal|kidney disease stage", re.I)
DIABETES = re.compile(r"diabet|T2DM", re.I)


def load(path: Path):
    return [json.loads(l) for s in SPLITS for l in open(path / f"{s}.jsonl")]


def parse_date(s: str):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    return None


def parse_name(s: str):
    s = s.strip()
    if "," in s:
        last, first = [x.strip() for x in s.split(",", 1)]
    else:
        parts = s.split()
        first, last = parts[0], " ".join(parts[1:])
    return first.title(), last.title()


def pct(x):
    return f"{100 * x:.1f}%"


def tv_distance(p: dict, q: dict) -> float:
    return 0.5 * sum(abs(p.get(k, 0) - q.get(k, 0)) for k in set(p) | set(q))


def entropy_ratio(c: Counter) -> float:
    n = sum(c.values())
    h = -sum(v / n * math.log(v / n) for v in c.values())
    return h / math.log(len(c)) if len(c) > 1 else 0.0


def analyse(docs: list[dict]) -> dict:
    clean = [d for d in docs if not d["ocr"]]
    by_episode = defaultdict(list)
    for d in docs:
        by_episode[d["episode_id"]].append(d)

    # Patient identity from clean claim forms (every episode has one).
    patients = {}
    episodes = {}
    for d in clean:
        if d["doc_type"] != "claim_form":
            continue
        dob_span = next((p for p in d["pii"] if p["label"] == "DATE_OF_BIRTH"), None)
        name_span = next((p for p in d["pii"] if p["label"] == "NAME"), None)
        dob = parse_date(dob_span["text"]) if dob_span else None
        svc = d["fields"].get("service_date")
        ep = {"diag": d["fields"]["diagnosis"], "dob": dob, "patient": d["patient_id"],
              "service": date.fromisoformat(svc) if svc else None,
              "injected": bool(d["injected_signals"]), "name": parse_name(name_span["text"]) if name_span else None}
        episodes[d["episode_id"]] = ep
        if dob and ep["name"]:
            patients.setdefault(d["patient_id"], {"dob": dob, "name": ep["name"], "first_service": ep["service"]})

    out = {"documents": len(docs), "patients": len({d["patient_id"] for d in docs}), "episodes": len(by_episode)}

    # A1. Age mix at first service
    ages = []
    for p in patients.values():
        if p["first_service"] and p["first_service"] > p["dob"]:
            ages.append((p["first_service"] - p["dob"]).days / 365.25)
    bands = Counter("0-17" if a < 18 else "18-64" if a < 65 else "65+" for a in ages)
    dist = {k: bands[k] / len(ages) for k in CENSUS_AGE}
    out["age"] = {"n": len(ages), "dist": dist, "median": round(statistics.median(ages), 1),
                  "tv_vs_census": round(tv_distance(dist, CENSUS_AGE), 3)}

    # A2. Names
    firsts = [p["name"][0].lower() for p in patients.values()]
    lasts = [p["name"][1].lower() for p in patients.values()]
    full = Counter(p["name"] for p in patients.values())
    out["names"] = {
        "first_in_us_list": sum(f in FIRST_NAMES for f in firsts) / len(firsts),
        "last_in_us_list": sum(l in LAST_NAMES for l in lasts) / len(lasts),
        "distinct_first_per_100": 100 * len(set(firsts)) / len(firsts),
        "distinct_last_per_100": 100 * len(set(lasts)) / len(lasts),
        "patients_sharing_full_name": sum(c for c in full.values() if c > 1) / len(full),
    }

    # B1. Impossible or implausible combinations (no injected signs)
    eps = [e for e in episodes.values() if not e["injected"] and e["dob"] and e["service"]]
    n_ob = n_ob_bad = n_child = n_child_adult_dx = n_male_ob = 0
    for e in eps:
        age = (e["service"] - e["dob"]).days / 365.25
        first = e["name"][0].lower() if e["name"] else ""
        if OBSTETRIC.search(e["diag"]):
            n_ob += 1
            n_ob_bad += not (12 <= age <= 55)
            n_male_ob += first in MALE_ONLY
        if age < 18:
            n_child += 1
            n_child_adult_dx += bool(ADULT_ONLY.search(e["diag"]))
    out["plausibility"] = {
        "episodes_checked": len(eps),
        "obstetric_episodes": n_ob,
        "obstetric_outside_age_12_55": n_ob_bad,
        "obstetric_with_male_only_name": n_male_ob,
        "child_episodes": n_child,
        "child_with_adult_only_diagnosis": n_child_adult_dx,
    }

    # B2. Lab values that fit the diagnosis: HbA1c in diabetic vs other episodes
    a1c = {"diabetic": [], "other": []}
    for eid, ds in by_episode.items():
        e = episodes.get(eid)
        if not e or e["injected"]:
            continue
        for d in ds:
            if d["doc_type"] == "lab_report" and not d["ocr"]:
                for t in d["fields"]["tests"]:
                    if t["name"].lower().startswith("hemoglobin a1c"):
                        a1c["diabetic" if DIABETES.search(e["diag"]) else "other"].append(t["value"])
    out["hba1c"] = {k: {"n": len(v), "median": round(statistics.median(v), 2) if v else None,
                        "share_ge_6_5": round(sum(x >= 6.5 for x in v) / len(v), 3) if v else None}
                    for k, v in a1c.items()}

    # B3. Multimorbidity by age: distinct diagnoses per patient
    diags_by_patient = defaultdict(set)
    for e in episodes.values():
        diags_by_patient[e["patient"]].add(e["diag"].lower())
    mm = defaultdict(list)
    for pid, p in patients.items():
        if p["first_service"] and p["first_service"] > p["dob"]:
            age = (p["first_service"] - p["dob"]).days / 365.25
            mm["<45" if age < 45 else "45-64" if age < 65 else "65+"].append(len(diags_by_patient[pid]))
    out["multimorbidity"] = {k: round(statistics.mean(v), 2) for k, v in sorted(mm.items())}

    # C1. Stays: length and cost
    los, stay_cost = [], []
    for d in docs:
        f = d["fields"]
        if d["doc_type"] == "hospital_bill" and not d["injected_signals"] and f["admission_date"] and f["discharge_date"]:
            n = (date.fromisoformat(f["discharge_date"]) - date.fromisoformat(f["admission_date"])).days
            if n > 0:
                los.append(n)
                stay_cost.append(f["total_billed"])
    out["stays"] = {"share_of_episodes_with_stay": round(len(los) / max(1, len(by_episode)), 3),
                    "n": len(los), "los_mean": round(statistics.mean(los), 2), "los_median": statistics.median(los),
                    "cost_median": round(statistics.median(stay_cost)), "cost_mean": round(statistics.mean(stay_cost))}

    # C2. Diagnosis mix
    dx = Counter(e["diag"].lower() for e in episodes.values())
    top5 = sum(v for _, v in dx.most_common(5)) / sum(dx.values())
    out["diagnoses"] = {"distinct": len(dx), "top5_share": round(top5, 3), "evenness": round(entropy_ratio(dx), 3),
                        "top": dx.most_common(8)}
    procs = Counter(p.lower() for d in docs if d["doc_type"] == "claim_form" for p in d["fields"]["procedure"])
    meds = Counter(m["name"].lower() for d in docs if d["doc_type"] == "prescription" for m in d["fields"]["medicines"])
    tests = Counter(t["name"].lower() for d in docs if d["doc_type"] == "lab_report" for t in d["fields"]["tests"])
    out["vocabulary"] = {"distinct_procedures": len(procs), "distinct_medicines": len(meds), "distinct_lab_tests": len(tests),
                         "distinct_providers": len({d["fields"]["provider"] for d in docs if d["doc_type"] == "claim_form" and d["fields"]["provider"]})}

    # D. Identifier surface realism (clean docs only)
    phones = [re.sub(r"\D", "", p["text"]) for d in clean for p in d["pii"] if p["label"] == "PHONE"]
    emails = [p["text"].split("@")[-1].lower() for d in clean for p in d["pii"] if p["label"] == "EMAIL"]
    addrs = [p["text"] for d in clean for p in d["pii"] if p["label"] == "ADDRESS"]
    zip_ok = 0
    for a in addrs:
        m = re.search(r"\b([A-Z]{2}) (\d{5})$", a)
        zip_ok += bool(m and m.group(1) in ZIP_REGION[m.group(2)[0]].split())
    out["identifiers"] = {
        # Fictional numbers: 555 as area code (in-house) or the reserved 555-0100..0199 block.
        "phones_fictional": round(sum(p.startswith("555") or p[3:8] == "55501" for p in phones) / len(phones), 3),
        "emails_on_reserved_domains": round(sum(e.endswith((".test", "example.com", "example.org", "example.net")) for e in emails) / len(emails), 3),
        "distinct_email_domains": len(set(emails)),
        "zip_matches_state": round(zip_ok / len(addrs), 3),
        "distinct_cities": len({a.rsplit(",", 2)[-2].strip() for a in addrs if a.count(",") >= 2}),
    }
    return out


def main():
    res = {name: analyse(load(path)) for name, path in CORPORA.items()}
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "realism_stats.json").write_text(json.dumps(res, indent=2, default=str) + "\n")
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
