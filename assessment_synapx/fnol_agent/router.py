from typing import Dict, Any, List, Tuple
import json

MANDATORY_FIELDS = [
    "Policy Number",
    "Policyholder Name",
    "Effective Dates",
    "Date",
    "Location",
    "Description",
    "Claimant",
    "Asset Type",
    "Initial Estimate",
    "Claim Type",
]


def find_missing(fields: Dict[str, Any]) -> List[str]:
    missing = []
    for f in MANDATORY_FIELDS:
        val = fields.get(f)
        if val is None or (isinstance(val, str) and val.strip() == ""):
            missing.append(f)
        elif isinstance(val, (list, dict)) and len(val) == 0:
            missing.append(f)
    return missing


def route_and_reason(fields: Dict[str, Any], missing: List[str]) -> Tuple[str, str]:
    desc = (fields.get("Description") or "").lower()
    fraud_words = ["fraud", "inconsistent", "staged", "intentional"]
    est = fields.get("Initial Estimate")
    claim_type = (fields.get("Claim Type") or "").lower()

    if missing:
        return "Manual Review", f"Missing mandatory fields: {', '.join(missing)}"

    if any(w in desc for w in fraud_words):
        found = [w for w in fraud_words if w in desc]
        return "Investigation Flag", f"Description contains suspicious words: {', '.join(found)}"

    if claim_type and "injur" in claim_type:
        return "Specialist Queue", "Claim type indicates injury; route to specialist"

    if isinstance(est, (int, float)):
        try:
            if est < 25000:
                return "Fast-track", f"Estimated damage ${est:,.2f} is below 25,000"
            else:
                return "Standard Queue", f"Estimated damage ${est:,.2f} exceeds fast-track threshold"
        except Exception:
            pass

    return "Standard Queue", "No special routing rule matched"


def build_output(fields: Dict[str, Any]) -> Dict[str, Any]:
    missing = find_missing(fields)
    route, reason = route_and_reason(fields, missing)

    extracted = {}
    for k, v in fields.items():
        if isinstance(v, (str, int, float)) or v is None:
            extracted[k] = v
        else:
            try:
                extracted[k] = json.loads(json.dumps(v))
            except Exception:
                extracted[k] = str(v)

    return {
        "extractedFields": extracted,
        "missingFields": missing,
        "recommendedRoute": route,
        "reasoning": reason,
    }