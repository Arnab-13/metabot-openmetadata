import spacy
import re

nlp = spacy.load("en_core_web_sm")

PII_COLUMN_PATTERNS = [
    "email", "phone", "mobile", "ssn", "social_security",
    "passport", "credit_card", "card_number", "dob",
    "date_of_birth", "address", "zip_code", "postal_code",
    "national_id", "aadhaar", "pan_number", "first_name",
    "last_name", "full_name", "gender", "salary",
    "account_number", "bank_account", "ip_address"
]

# Removed "age" from patterns — too many false positives

def detect_pii_columns(columns: list) -> list:
    flagged = []
    seen = set()

    for col in columns:
        col_name = col.get("name", "unknown")
        name = col_name.lower()
        description = col.get("description", "").lower()

        if col_name in seen:
            continue

        # Split column name by underscores and check each word
        # This prevents 'age' matching inside 'average' or 'usage'
        name_parts = re.split(r'[_\s]+', name)

        for pattern in PII_COLUMN_PATTERNS:
            pattern_parts = re.split(r'[_\s]+', pattern)
            # Check if ALL parts of the pattern appear as whole words
            if all(p in name_parts for p in pattern_parts):
                flagged.append({
                    "column": col_name,
                    "dataType": col.get("dataType", "unknown"),
                    "reason": f"column name matches '{pattern}'",
                    "confidence": "high"
                })
                seen.add(col_name)
                break

        # NLP on description — tighter filter
        # Only flag PERSON and GPE (location) as truly sensitive
        if col_name not in seen and description:
            doc = nlp(description)
            truly_sensitive = ["PERSON", "GPE", "LOC"]
            matched = [ent.label_ for ent in doc.ents if ent.label_ in truly_sensitive]
            if matched:
                flagged.append({
                    "column": col_name,
                    "dataType": col.get("dataType", "unknown"),
                    "reason": f"description mentions sensitive entities: {list(set(matched))}",
                    "confidence": "medium"
                })
                seen.add(col_name)

    return flagged


def summarize_pii_findings(table_name: str, flagged: list) -> str:
    if not flagged:
        return f"No PII columns detected in {table_name}."

    high = [f for f in flagged if f["confidence"] == "high"]
    medium = [f for f in flagged if f["confidence"] == "medium"]

    lines = [f"Found {len(flagged)} potential PII column(s) in {table_name}:"]

    if high:
        lines.append(f"\n  High confidence ({len(high)}):")
        for f in high:
            lines.append(f"    - {f['column']} ({f['dataType']}) — {f['reason']}")

    if medium:
        lines.append(f"\n  Medium confidence ({len(medium)}):")
        for f in medium:
            lines.append(f"    - {f['column']} ({f['dataType']}) — {f['reason']}")

    return "\n".join(lines)