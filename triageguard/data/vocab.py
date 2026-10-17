"""Word lists used to build synthetic patients and documents.

Everything here is invented or generic. Phone numbers use the reserved 555
exchange and SSNs use the 900-999 area range, which the SSA never issues, so
no generated identifier can belong to a real person.
"""

FIRST_NAMES = [
    "Jane", "Maria", "Aisha", "Priya", "Chen", "Olivia", "Fatima", "Sofia", "Emily", "Grace",
    "Hannah", "Isabel", "Leah", "Mei", "Nadia", "Rosa", "Sara", "Tara", "Yuki", "Zoe",
    "Ananya", "Beatriz", "Camila", "Deborah", "Elena", "Farah", "Gloria", "Ingrid", "Julia", "Keisha",
    "James", "Robert", "Michael", "David", "Daniel", "Carlos", "Ahmed", "Raj", "Wei", "Liam",
    "Noah", "Omar", "Pedro", "Samuel", "Thomas", "Victor", "William", "Kenji", "Arjun", "Diego",
    "Ethan", "Felix", "Gabriel", "Hiro", "Ivan", "Jamal", "Kwame", "Luis", "Mateo", "Nikhil",
    "Oscar", "Paul", "Quentin", "Ravi", "Stefan", "Tomas", "Umar", "Vikram", "Xavier", "Yusuf",
]

LAST_NAMES = [
    "Rivera", "Smith", "Johnson", "Williams", "Brown", "Garcia", "Martinez", "Lee", "Patel", "Nguyen",
    "Kim", "Chen", "Singh", "Khan", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor",
    "Moore", "Jackson", "Martin", "Thompson", "White", "Harris", "Clark", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Hill", "Flores", "Green", "Adams",
    "Nelson", "Baker", "Hall", "Campbell", "Mitchell", "Carter", "Roberts", "Okafor", "Mensah", "Sharma",
    "Iyer", "Tanaka", "Sato", "Ivanova", "Kowalski", "Novak", "Haddad", "Rahman", "Ali", "Fernandes",
    "O'Brien", "McAllister", "Van der Berg", "De la Cruz", "Nakamura", "Abernathy", "Delgado", "Bauer", "Romero", "Castillo",
]

STREET_NAMES = [
    "Maple", "Oak", "Pine", "Cedar", "Elm", "Willow", "Birch", "Lakeview", "Hillcrest", "Sunset",
    "Riverside", "Park", "Washington", "Lincoln", "Jefferson", "Highland", "Meadow", "Spring", "Valley", "Forest",
]
STREET_SUFFIXES = ["St", "Street", "Ave", "Avenue", "Rd", "Road", "Blvd", "Lane", "Dr", "Court"]

# (city, state, zip prefix) - the ZIP suffix is random.
CITIES = [
    ("Springfield", "IL", "627"), ("Riverton", "WY", "825"), ("Fairview", "TX", "750"),
    ("Madison", "WI", "537"), ("Georgetown", "KY", "403"), ("Franklin", "TN", "370"),
    ("Clinton", "IA", "527"), ("Salem", "OR", "973"), ("Greenville", "SC", "296"),
    ("Bristol", "CT", "060"), ("Arlington", "VA", "222"), ("Dayton", "OH", "454"),
    ("Burlington", "VT", "054"), ("Fresno", "CA", "937"), ("Tucson", "AZ", "857"),
    ("Albany", "NY", "122"), ("Augusta", "ME", "043"), ("Boise", "ID", "837"),
]

EMAIL_DOMAINS = ["example.com", "mailbox.test", "inbox.example.org", "post.example.net"]

# Providers are organisations, not people, so they are a field and not PII.
PROVIDERS_GENERAL = [
    "St. Mary Regional Medical Center", "Lakeside General Hospital", "Northview Community Hospital",
    "Cedar Valley Health System", "Riverbend Medical Center", "Pinecrest Family Practice",
]
# Specialty providers are only used for diagnoses in their family.
PROVIDERS_SPECIALTY = {
    "ortho": ["Greenfield Orthopedic Associates", "Harborview Surgical Institute"],
    "gastro": ["Harborview Surgical Institute"],
    "cardiac": ["Mercy Heart and Vascular Center"],
    "oncology": ["Brightwater Cancer Institute"],
    "mental": ["Summit Specialty Clinic"],
    "renal": ["Summit Specialty Clinic"],
}
PROVIDERS = PROVIDERS_GENERAL + sorted({p for v in PROVIDERS_SPECIALTY.values() for p in v})
LABS = [
    "Oakridge Diagnostic Labs", "Precision Pathology Services", "ClearPath Laboratories",
    "Metro Clinical Lab", "Sunrise Reference Laboratory",
]
PHARMACIES = ["Main Street Pharmacy", "CareWell Pharmacy", "QuickRx Drugs", "Hillside Apothecary"]
INSURERS = ["BlueRiver Health Plan", "Evergreen Mutual Insurance", "Unity Care Assurance", "Keystone Health TPA"]

# Diagnosis -> compatible procedures. A "procedure mismatch" draws a procedure
# from a different diagnosis family.
# Each diagnosis: (ICD-10 code, wording variants, family)
DIAGNOSES = [
    ("E11.22", ["type 2 diabetes with kidney complications", "type 2 diabetes mellitus with diabetic chronic kidney disease", "T2DM with diabetic nephropathy"], "endocrine"),
    ("E11.9", ["type 2 diabetes without complications", "type 2 diabetes mellitus, uncomplicated", "T2DM, controlled"], "endocrine"),
    ("I21.4", ["acute non-ST elevation myocardial infarction", "NSTEMI", "non-ST elevation heart attack"], "cardiac"),
    ("I50.9", ["congestive heart failure", "heart failure, unspecified", "CHF exacerbation"], "cardiac"),
    ("I48.91", ["atrial fibrillation", "unspecified atrial fibrillation", "AFib with rapid ventricular response"], "cardiac"),
    ("J18.9", ["community acquired pneumonia", "pneumonia, unspecified organism", "lobar pneumonia"], "respiratory"),
    ("J44.1", ["COPD with acute exacerbation", "chronic obstructive pulmonary disease with exacerbation", "acute exacerbation of COPD"], "respiratory"),
    ("J45.40", ["moderate persistent asthma", "asthma, moderate persistent", "persistent asthma, moderate"], "respiratory"),
    ("K35.80", ["acute appendicitis", "acute appendicitis without perforation", "uncomplicated appendicitis"], "gastro"),
    ("K80.20", ["gallstones without obstruction", "cholelithiasis", "symptomatic gallstones"], "gastro"),
    ("M17.11", ["primary osteoarthritis of the right knee", "right knee osteoarthritis", "OA of right knee"], "ortho"),
    ("S72.001A", ["fracture of the right femoral neck", "right hip fracture", "closed fracture of femur neck"], "ortho"),
    ("M54.5", ["low back pain", "lumbago", "chronic lower back pain"], "ortho"),
    ("N39.0", ["urinary tract infection", "UTI, site not specified", "acute cystitis"], "renal"),
    ("N18.4", ["chronic kidney disease stage 4", "CKD stage IV", "severe chronic kidney disease"], "renal"),
    ("C50.911", ["malignant neoplasm of the right breast", "right breast cancer", "breast carcinoma, right"], "oncology"),
    ("C34.90", ["lung cancer", "malignant neoplasm of lung", "non-small cell lung carcinoma"], "oncology"),
    ("F32.9", ["major depressive disorder", "depression, single episode", "major depression"], "mental"),
    ("I10", ["essential hypertension", "high blood pressure", "primary hypertension"], "cardiac"),
    ("O80", ["normal delivery", "uncomplicated vaginal delivery", "full-term normal delivery"], "obstetric"),
]

# procedure name, CPT-like code, family, typical cost range, inpatient?
PROCEDURES = [
    ("hemodialysis session", "90935", "renal", (450, 1200), False),
    ("kidney ultrasound", "76770", "renal", (300, 900), False),
    ("cystoscopy", "52000", "renal", (900, 2500), False),
    ("insulin pump fitting", "S1034", "endocrine", (2500, 7000), False),
    ("diabetic foot examination", "G0245", "endocrine", (120, 400), False),
    ("coronary angioplasty with stent", "92928", "cardiac", (18000, 45000), True),
    ("echocardiogram", "93306", "cardiac", (800, 2500), False),
    ("cardiac catheterization", "93458", "cardiac", (6000, 15000), True),
    ("electrical cardioversion", "92960", "cardiac", (3000, 9000), True),
    ("chest x-ray", "71046", "respiratory", (150, 500), False),
    ("bronchoscopy", "31622", "respiratory", (2500, 6000), False),
    ("pulmonary function test", "94010", "respiratory", (200, 700), False),
    ("laparoscopic appendectomy", "44970", "gastro", (9000, 22000), True),
    ("laparoscopic cholecystectomy", "47562", "gastro", (10000, 25000), True),
    ("upper GI endoscopy", "43235", "gastro", (1500, 4000), False),
    ("total knee replacement", "27447", "ortho", (25000, 55000), True),
    ("hip hemiarthroplasty", "27125", "ortho", (22000, 48000), True),
    ("lumbar MRI", "72148", "ortho", (900, 3000), False),
    ("physical therapy session", "97110", "ortho", (90, 300), False),
    ("lumpectomy", "19301", "oncology", (8000, 20000), True),
    ("chemotherapy infusion", "96413", "oncology", (3000, 12000), False),
    ("CT-guided lung biopsy", "32405", "oncology", (4000, 10000), False),
    ("psychotherapy session", "90837", "mental", (120, 350), False),
    ("psychiatric evaluation", "90792", "mental", (250, 600), False),
    ("vaginal delivery", "59400", "obstetric", (6000, 15000), True),
    ("obstetric ultrasound", "76805", "obstetric", (300, 900), False),
]

# test name, unit, normal low, normal high
LAB_TESTS = [
    ("Hemoglobin A1c", "%", 4.0, 5.6),
    ("Fasting glucose", "mg/dL", 70, 99),
    ("Serum creatinine", "mg/dL", 0.6, 1.2),
    ("eGFR", "mL/min/1.73m2", 90, 120),
    ("Troponin I", "ng/mL", 0.0, 0.04),
    ("BNP", "pg/mL", 0, 100),
    ("White blood cell count", "x10^3/uL", 4.5, 11.0),
    ("Hemoglobin", "g/dL", 12.0, 17.5),
    ("Platelet count", "x10^3/uL", 150, 400),
    ("Sodium", "mmol/L", 135, 145),
    ("Potassium", "mmol/L", 3.5, 5.1),
    ("ALT", "U/L", 7, 56),
    ("Total cholesterol", "mg/dL", 125, 200),
    ("LDL cholesterol", "mg/dL", 0, 100),
    ("TSH", "mIU/L", 0.4, 4.0),
    ("C-reactive protein", "mg/L", 0, 10),
]

# medicine, strengths, families it suits
MEDICINES = [
    ("Metformin", ["500 mg", "850 mg", "1000 mg"], "endocrine"),
    ("Insulin glargine", ["10 units", "20 units", "30 units"], "endocrine"),
    ("Empagliflozin", ["10 mg", "25 mg"], "endocrine"),
    ("Atorvastatin", ["20 mg", "40 mg", "80 mg"], "cardiac"),
    ("Metoprolol succinate", ["25 mg", "50 mg", "100 mg"], "cardiac"),
    ("Apixaban", ["2.5 mg", "5 mg"], "cardiac"),
    ("Lisinopril", ["10 mg", "20 mg"], "cardiac"),
    ("Furosemide", ["20 mg", "40 mg"], "cardiac"),
    ("Amoxicillin-clavulanate", ["875 mg"], "respiratory"),
    ("Azithromycin", ["250 mg", "500 mg"], "respiratory"),
    ("Albuterol inhaler", ["90 mcg"], "respiratory"),
    ("Tiotropium", ["18 mcg"], "respiratory"),
    ("Ondansetron", ["4 mg", "8 mg"], "gastro"),
    ("Pantoprazole", ["20 mg", "40 mg"], "gastro"),
    ("Oxycodone", ["5 mg", "10 mg"], "ortho"),
    ("Ibuprofen", ["400 mg", "600 mg", "800 mg"], "ortho"),
    ("Nitrofurantoin", ["100 mg"], "renal"),
    ("Calcitriol", ["0.25 mcg"], "renal"),
    ("Tamoxifen", ["20 mg"], "oncology"),
    ("Sertraline", ["50 mg", "100 mg"], "mental"),
    ("Prenatal vitamins", ["1 tablet"], "obstetric"),
]

FREQUENCIES = ["once daily", "twice daily", "three times daily", "every 8 hours", "at bedtime", "as needed"]
DURATIONS = ["7 days", "10 days", "14 days", "30 days", "90 days"]
