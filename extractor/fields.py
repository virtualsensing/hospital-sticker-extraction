"""Field schema, validation, and formatting for extracted sticker data."""

import re
from datetime import datetime

# Canonical field order and labels
FIELDS = [
    "hospital_name",
    "patient_number",
    "patient_name",
    "ward",
    "admitted",
    "date_of_birth",
    "age",
    "sex",
    "patient_id",
    "medical_aid_and_plan",
    "med_aid_number",
    "member_name",
    "member_id",
    "doctor",
    "phone",
    "email",
]

# Human-readable labels for display and CSV headers
FIELD_LABELS = {
    "hospital_name": "Hospital Name",
    "patient_number": "Patient Number",
    "patient_name": "Patient Name",
    "ward": "Ward",
    "admitted": "Admitted",
    "date_of_birth": "Date of Birth",
    "age": "Age",
    "sex": "Sex",
    "patient_id": "Patient ID",
    "medical_aid_and_plan": "Medical Aid & Plan",
    "med_aid_number": "Med Aid Number",
    "member_name": "Member Name",
    "member_id": "Member ID",
    "doctor": "Doctor",
    "phone": "Phone",
    "email": "Email",
}

# Titles to strip from patient names
TITLES = {"mr", "mrs", "ms", "miss", "master", "dr", "prof"}

# Month abbreviations for DOB formatting
MONTHS = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def format_dob(raw: str) -> str:
    """Convert various DOB formats to 'dd Mon yyyy'.

    Handles:
      - dd/mm/yyyy  (e.g. 20/02/1949)
      - dd/mm/yy    (e.g. 06/12/46)
      - Already formatted (e.g. 20 Feb 1949) — returned as-is
    """
    if not raw or not raw.strip():
        return ""

    raw = raw.strip()

    # Already in target format
    if re.match(r"^\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}$", raw):
        return raw

    # Try dd/mm/yyyy or dd/mm/yy
    match = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$", raw)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))

        # Expand 2-digit year
        if year < 100:
            # Assume 00-29 = 2000s, 30-99 = 1900s
            year = 2000 + year if year < 30 else 1900 + year

        month_name = MONTHS.get(month, "???")
        return f"{day:02d} {month_name} {year}"

    return raw  # Return as-is if we can't parse


def format_patient_name(raw: str) -> str:
    """Convert 'Surname FirstName Title' or 'SURNAME FIRSTNAME TITLE' to 'FirstName Surname'.

    Strips titles (Mr, Mrs, Ms, Miss, Master, Dr, Prof).
    Handles both 'Surname FirstName Mr' and 'MR FIRSTNAME SURNAME' formats.
    """
    if not raw or not raw.strip():
        return ""

    parts = raw.strip().split()

    # Remove titles
    cleaned = [p for p in parts if p.lower().rstrip(".,") not in TITLES]

    if not cleaned:
        return raw.strip()

    # Title case each part
    cleaned = [p.capitalize() if p.isupper() else p for p in cleaned]

    # If first part looks like a surname (sticker format: Surname First Middle),
    # move it to the end: [Surname, First, Middle] -> [First, Middle, Surname]
    # Heuristic: if the original had a title at the end (Mr, Mrs etc.), the first
    # word is the surname.
    original_parts_lower = [p.lower().rstrip(".,") for p in parts]
    title_at_end = len(parts) >= 2 and original_parts_lower[-1] in TITLES
    title_at_start = len(parts) >= 2 and original_parts_lower[0] in TITLES

    if title_at_end and len(cleaned) >= 2:
        # Sticker format: "Surname FirstName(s) Title" → reorder
        surname = cleaned[0]
        first_names = cleaned[1:]
        return " ".join(first_names + [surname])
    elif title_at_start and len(cleaned) >= 2:
        # Format: "MR FIRSTNAME SURNAME" → already correct order after title removal
        return " ".join(cleaned)

    # Default: return as-is (already in correct order or ambiguous)
    return " ".join(cleaned)


def format_doctor(raw: str) -> str:
    """Convert various doctor name formats to 'Dr [Initials] [Surname]'.

    Handles:
      - 'Jones (0551234) D, DR'  → 'Dr D Jones'
      - 'Dr D Jones'             → 'Dr D Jones' (already correct)
      - 'DR D JONES'             → 'Dr D Jones'
    """
    if not raw or not raw.strip():
        return ""

    raw = raw.strip()

    # Already in 'Dr X Y' format
    if re.match(r"^Dr\s+\S", raw):
        return raw

    # Hibiscus format: 'Surname (PracticeNo) Initials, DR'
    match = re.match(
        r"^(\w+)\s*\(\d+\)\s*([A-Z,\s]+),?\s*DR$", raw, re.IGNORECASE
    )
    if match:
        surname = match.group(1).capitalize()
        initials = match.group(2).strip().rstrip(",").strip()
        return f"Dr {initials} {surname}"

    # 'DR FIRSTNAME SURNAME' format
    if raw.upper().startswith("DR "):
        name_part = raw[3:].strip()
        parts = name_part.split()
        parts = [p.capitalize() if len(p) > 2 and p.isupper() else p for p in parts]
        return f"Dr {' '.join(parts)}"

    return raw


def format_ward(raw: str) -> str:
    """Extract just the ward type (SURG, MED, DAY), dropping bed/room numbers."""
    if not raw or not raw.strip():
        return ""

    raw = raw.strip().upper()

    # Extract the ward type keyword
    for ward in ["SURG", "MED", "DAY", "ICU", "MATERNITY", "PAED", "ORTHO"]:
        if ward in raw:
            return ward

    return raw


def format_phone(cell: str, tel: str) -> str:
    """Return cell number preferentially, fallback to telephone."""
    for num in [cell, tel]:
        if num and num.strip() and num.strip() not in ("(W)", "(H)", "", "-"):
            return num.strip()
    return ""


def combine_medical_aid(med_aid: str, med_scheme: str, scheme_field: str = "") -> str:
    """Combine medical aid and scheme/plan into a single string.

    Handles:
      - Shelly Beach: Med Aid = 'DISCOVERY HEALTH MED', Scheme = 'COASTAL SAVER'
        → 'Discovery Coastal Saver'
      - Hibiscus: Scheme = 'Momentum Associated' (single field)
        → 'Momentum Associated'
      - COID: Med Aid = 'COID', Scheme = employer name
        → 'COID [Employer]'
    """
    # Hibiscus uses a single "Scheme" field for the combined value
    if scheme_field and not med_aid:
        return _title_case_aid(scheme_field)

    aid = (med_aid or "").strip()
    scheme = (med_scheme or "").strip()

    if not aid and not scheme:
        return ""

    # COID — keep uppercase, append employer if available
    if aid.upper() == "COID":
        if scheme:
            return f"COID {_title_case_aid(scheme)}"
        return "COID"

    # Simplify common medical aid names
    aid_clean = _simplify_aid_name(aid)
    scheme_clean = _title_case_aid(scheme) if scheme else ""

    if scheme_clean and scheme_clean.lower() != aid_clean.lower():
        return f"{aid_clean} {scheme_clean}"
    return aid_clean


def _simplify_aid_name(name: str) -> str:
    """Simplify verbose medical aid names."""
    name = name.strip()
    # 'DISCOVERY HEALTH MED' → 'Discovery'
    if "DISCOVERY" in name.upper():
        return "Discovery"
    # 'GEMS NON DENTAL' → 'Gems Non Dental'
    return _title_case_aid(name)


def _title_case_aid(s: str) -> str:
    """Title-case a medical aid/scheme name."""
    if not s:
        return ""
    return " ".join(word.capitalize() for word in s.strip().split())


def validate_record(record: dict) -> list[str]:
    """Return a list of warnings for a parsed record."""
    warnings = []

    if not record.get("hospital_name"):
        warnings.append("Missing hospital name")
    if not record.get("patient_name"):
        warnings.append("Missing patient name")
    if not record.get("patient_id"):
        warnings.append("Missing patient ID")

    pid = record.get("patient_id", "")
    if pid and not re.match(r"^\d{13}$", pid):
        warnings.append(f"Patient ID '{pid}' is not a valid 13-digit SA ID")

    dob = record.get("date_of_birth", "")
    if dob and not re.match(r"^\d{2}\s+[A-Z][a-z]{2}\s+\d{4}$", dob):
        warnings.append(f"Date of birth '{dob}' not in expected format 'dd Mon yyyy'")

    return warnings
