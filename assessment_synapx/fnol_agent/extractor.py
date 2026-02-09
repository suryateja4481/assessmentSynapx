import re
from typing import List, Optional, Dict, Any

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None


def read_pdf_text(path: str) -> str:
    """Extract text from a PDF using PyPDF2."""
    if PdfReader is None:
        raise RuntimeError("PyPDF2 not installed. Install dependencies from requirements.txt")
    text_parts: List[str] = []
    reader = PdfReader(path)
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            try:
                text_parts.append(page.extract_text() or "")
            except Exception:
                pass
    return "\n".join(text_parts)


def read_pdf_form_fields(path: str) -> Dict[str, str]:
    """Read AcroForm fields from a PDF. Returns a mapping of field name -> value.

    Uses PyPDF2 form APIs where available. Empty if no form found.
    """
    result: Dict[str, str] = {}
    if PdfReader is None:
        raise RuntimeError("PyPDF2 not installed. Install dependencies from requirements.txt")
    reader = PdfReader(path)
    # PyPDF2 exposes form fields via get_fields() in many versions
    fields = {}
    try:
        # get_fields may return None or dict
        if hasattr(reader, "get_fields"):
            fields = reader.get_fields() or {}
        elif hasattr(reader, "fields"):
            fields = reader.fields or {}
    except Exception:
        fields = {}

    # fields could be a mapping fieldname -> fieldObj (with /V value)
    for k, v in (fields.items() if isinstance(fields, dict) else []):
        try:
            # v might be a dict-like with '/V' or 'value'
            if isinstance(v, dict):
                val = v.get("/V") or v.get("V") or v.get("value")
            else:
                # fallback: string
                val = str(v)
            if val is not None:
                result[k] = str(val)
        except Exception:
            continue
    # Some PDFs have AcroForm as /AcroForm in the trailer - try a second approach
    try:
        catalog = reader.trailer['/Root']
        acro = catalog.get('/AcroForm') if catalog is not None else None
        if acro and '/Fields' in acro:
            for f in acro['/Fields']:
                try:
                    obj = f.get_object()
                    name = obj.get('/T')
                    val = obj.get('/V')
                    if name:
                        result[str(name)] = str(val) if val is not None else ""
                except Exception:
                    continue
    except Exception:
        pass

    return result


def find_first(patterns: List[str], text: str) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    return None


def extract_from_text_exact(text: str, labels: List[str]) -> Dict[str, str]:
    """Extract exact user-filled values from plain text using explicit labels.

    This expects the document/text to contain lines like "Policy Number: ABC123".
    Returns a mapping label->value for labels found.
    """
    out: Dict[str, str] = {}
    # Process line by line for deterministic extraction
    for line in text.splitlines():
        ln = line.strip()
        for label in labels:
            # match: label: value  OR label - value OR label value
            if re.match(rf"^{re.escape(label)}\s*[:\-\s]", ln, re.IGNORECASE):
                # capture after the first ':' or '-' if present
                parts = re.split(r"[:\-]", ln, maxsplit=1)
                if len(parts) > 1:
                    val = parts[1].strip()
                else:
                    # if no separator, remove label and take rest
                    val = re.sub(re.escape(label), "", ln, flags=re.IGNORECASE).strip()
                if val:
                    out[label] = val
    return out


def extract_from_file(path: str) -> Dict[str, Any]:
    """High-level extractor that tries to return exact user-filled fields.

    Strategy:
    - If the file is a PDF, first try to read AcroForm form fields (exact values).
    - If form fields found (non-empty), map known field keys to our target fields.
    - Otherwise, extract raw text and use deterministic label-based extraction.
    - For .txt files, use label-based extraction directly.
    """
    import os

    ext = os.path.splitext(path)[1].lower()
    labels = [
        "Policy Number", "Policyholder Name", "Effective Dates", "Date",
        "Time", "Location", "Description", "Claimant", "Third Parties",
        "Contact Details", "Asset Type", "Asset ID", "Initial Estimate",
        "Claim Type", "Attachments",
    ]

    # Try PDF form fields first
    if ext == ".pdf":
        try:
            form = read_pdf_form_fields(path)
            if form:
                # map form keys approximately to our labels (case-insensitive)
                def is_placeholder(val: str) -> bool:
                    if not val:
                        return True
                    v = val.strip()
                    if v == "":
                        return True
                    low = v.lower()
                    # common placeholders
                    placeholders = ["(mm/dd/yyyy)", "mm/dd/yyyy", "n/a", "na"]
                    if any(p in low for p in placeholders):
                        return True
                    if len(v) > 200:
                        return True
                    if "acord" in low or "page" in low:
                        return True
                    # if value looks like a set of prompts or contains many colons/question words,
                    # treat as placeholder (common in blank form templates)
                    if ":" in v:
                        prompts = ["where", "when", "describe", "estimate", "phone", "owner"]
                        cnt = sum(1 for p in prompts if p in low)
                        if cnt >= 1:
                            return True
                    # heavy uppercase indicative of a template heading
                    letters = [c for c in v if c.isalpha()]
                    if letters:
                        upper_frac = sum(1 for c in letters if c.isupper()) / len(letters)
                        if upper_frac > 0.6 and len(v) > 20:
                            return True
                    return False

                mapped: Dict[str, Any] = {}
                for label in labels:
                    found = None
                    for k, v in form.items():
                        if all(word.lower() in k.lower() for word in label.split() if len(word) > 2):
                            found = v
                            break
                    if found is None:
                        found = form.get(label) or form.get(label.replace(" ", "_"))
                    # normalize placeholders to None so they are not treated as filled values
                    try:
                        sval = str(found).strip() if found is not None else None
                    except Exception:
                        sval = None
                    if sval is None or is_placeholder(sval):
                        mapped[label] = None
                    else:
                        mapped[label] = sval
                return mapped
        except Exception:
            # fall back to text extraction
            pass

    # For txt or fallback, use deterministic text parsing
    if ext == ".txt" or True:
        text = read_pdf_text(path) if ext == ".pdf" else open(path, encoding="utf-8", errors="ignore").read()
        exact = extract_from_text_exact(text, labels)
        # sanitize extracted values: treat long/template-like values as None
        def sanitize(val: str) -> Optional[str]:
            if val is None:
                return None
            v = val.strip()
            if v == "":
                return None
            low = v.lower()
            if "acord" in low or "page" in low:
                return None
            if len(v) > 200:
                return None
            if low in ["n/a", "na"]:
                return None
            return v

        result: Dict[str, Any] = {L: sanitize(exact.get(L)) for L in labels}
        # Additionally keep raw text for advanced heuristics
        result["_raw_text"] = text
        # Coerce numeric-like estimate strings to floats so routing can compare numerically
        def try_parse_number(v):
            if v is None:
                return None
            if isinstance(v, (int, float)):
                return v
            s = str(v).strip().replace(',', '').replace('$', '')
            try:
                return float(s)
            except Exception:
                return v

        if "Initial Estimate" in result:
            result["Initial Estimate"] = try_parse_number(result["Initial Estimate"])
        if "Estimated Damage" in result:
            result["Estimated Damage"] = try_parse_number(result["Estimated Damage"])

        return result


def extract_fields(text: str) -> Dict[str, Any]:
    # Lightweight, heuristic-based field extraction.
    t = re.sub(r"\s+", " ", text)
    fields: Dict[str, Any] = {}

    fields["Policy Number"] = find_first([
        r"Policy(?:\sNo(?:\.|)|\sNumber)[:\s]*([A-Za-z0-9\-_/]+)",
        r"Policy #[:\s]*([A-Za-z0-9\-_/]+)",
    ], t)

    fields["Policyholder Name"] = find_first([
        r"Named Insured[:\s]*([A-Za-z ,.'-]{3,100})",
        r"Insured[:\s]*([A-Za-z ,.'-]{3,100})",
        r"Policyholder[:\s]*([A-Za-z ,.'-]{3,100})",
    ], t)

    eff = find_first([
        r"Policy Period[:\s]*([A-Za-z0-9, /\-]+)",
        r"Effective Date[:\s]*([A-Za-z0-9, /\-]+)",
        r"Effective[:\s]*([A-Za-z0-9, /\-]+)",
    ], t)
    fields["Effective Dates"] = eff

    fields["Date"] = find_first([
        r"Date of Loss[:\s]*([A-Za-z0-9,\-/ ]{4,40})",
        r"Accident Date[:\s]*([A-Za-z0-9,\-/ ]{4,40})",
        r"Loss Date[:\s]*([A-Za-z0-9,\-/ ]{4,40})",
    ], t)

    fields["Time"] = find_first([
        r"Time of Loss[:\s]*([0-2]?[0-9]:[0-5][0-9](?:\s?[APMapm]{2})?)",
        r"Time[:\s]*([0-2]?[0-9]:[0-5][0-9](?:\s?[APMapm]{2})?)",
    ], t)

    fields["Location"] = find_first([
        r"Location of Loss[:\s]*([A-Za-z0-9,\.\- /#]{5,200})",
        r"Location[:\s]*([A-Za-z0-9,\.\- /#]{5,200})",
    ], t)

    fields["Description"] = find_first([
        r"Description of Loss[:\s]*([\s\S]{10,400})",
        r"Describe the Loss[:\s]*([\s\S]{10,400})",
        r"Loss Description[:\s]*([\s\S]{10,400})",
    ], text)
    if fields["Description"]:
        fields["Description"] = re.sub(r"\s+", " ", fields["Description"]).strip()

    fields["Claimant"] = find_first([
        r"Claimant[:\s]*([A-Za-z ,.'-]{3,120})",
        r"Claimant Name[:\s]*([A-Za-z ,.'-]{3,120})",
        r"Name of Insured[:\s]*([A-Za-z ,.'-]{3,120})",
    ], t)

    fields["Third Parties"] = find_first([
        r"Third Party[:\s]*([A-Za-z ,.'-]{3,120})",
        r"Other Party[:\s]*([A-Za-z ,.'-]{3,120})",
    ], t)

    phone = re.search(r"(\+?\d[\d\-() ]{7,}\d)", t)
    email = re.search(r"([\w\.-]+@[\w\.-]+)", t)
    fields["Contact Details"] = {}
    if phone:
        fields["Contact Details"]["phone"] = phone.group(1).strip()
    if email:
        fields["Contact Details"]["email"] = email.group(1).strip()

    fields["Asset Type"] = find_first([
        r"Vehicle Type[:\s]*([A-Za-z0-9 ]{3,40})",
        r"Asset Type[:\s]*([A-Za-z0-9 ]{3,40})",
        r"Type of Vehicle[:\s]*([A-Za-z0-9 ]{3,40})",
    ], t)

    fields["Asset ID"] = find_first([
        r"VIN[:\s]*([A-HJ-NPR-Z0-9]{6,20})",
        r"Vehicle Identification Number[:\s]*([A-HJ-NPR-Z0-9]{6,20})",
        r"Serial Number[:\s]*([A-Za-z0-9\-]{4,40})",
    ], t)

    est = find_first([
        r"Estimated Loss[:\s]*\$?([0-9,]+(?:\.[0-9]{2})?)",
        r"Initial Estimate[:\s]*\$?([0-9,]+(?:\.[0-9]{2})?)",
        r"Estimate[:\s]*\$?([0-9,]+(?:\.[0-9]{2})?)",
        r"Total Estimated Loss[:\s]*\$?([0-9,]+(?:\.[0-9]{2})?)",
    ], t)
    if est:
        try:
            fields["Initial Estimate"] = float(est.replace(",", ""))
        except Exception:
            fields["Initial Estimate"] = est
        fields["Estimated Damage"] = fields["Initial Estimate"]
    else:
        fields["Initial Estimate"] = None

    claim_type = find_first([
        r"Claim Type[:\s]*([A-Za-z ]{3,40})",
        r"Type of Loss[:\s]*([A-Za-z ]{3,40})",
    ], t)
    if claim_type:
        fields["Claim Type"] = claim_type.lower()
    else:
        if re.search(r"injury|bodily injury|personal injury", t, re.IGNORECASE):
            fields["Claim Type"] = "injury"
        elif re.search(r"theft|stolen", t, re.IGNORECASE):
            fields["Claim Type"] = "theft"
        elif re.search(r"collision|accident|damage", t, re.IGNORECASE):
            fields["Claim Type"] = "property"
        else:
            fields["Claim Type"] = None

    attachments = find_first([
        r"Attachments?[:\s]*([A-Za-z0-9, \-_/]+)",
    ], t)
    fields["Attachments"] = attachments

    return fields
