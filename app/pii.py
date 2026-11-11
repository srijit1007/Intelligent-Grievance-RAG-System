
import re


_RULES = [
    # Email addresses
    (
        re.compile(
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            re.IGNORECASE
        ),
        "[EMAIL]"
    ),

    # Indian PAN numbers
    (
        re.compile(
            r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
            re.IGNORECASE
        ),
        "[PAN]"
    ),

    # Aadhaar-like 12-digit numbers
    # This detects the number pattern, not Aadhaar validity.
    (
        re.compile(
            r"(?<!\d)(?:\d{4}[ -]?){2}\d{4}(?!\d)"
        ),
        "[ID]"
    ),

    # Credit/debit card-like numbers (13–19 digits)
    (
        re.compile(
            r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"
        ),
        "[CARD]"
    ),

    # Indian phone numbers with optional +91 prefix
    (
        re.compile(
            r"(?<!\w)(?:\+91[\s-]?)?(?:0)?[6-9]\d{9}(?!\d)"
        ),
        "[PHONE]"
    ),

    # General international phone numbers
    (
        re.compile(
            r"(?<!\w)\+?\d[\d\s().-]{7,16}\d(?!\w)"
        ),
        "[PHONE]"
    ),

    # IPv4 addresses
    (
        re.compile(
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
        ),
        "[IP_ADDRESS]"
    ),
]


def redact(text: str) -> str:
    """
    Redact common personally identifiable information (PII).

    Returns the original text with detected patterns replaced
    by placeholder labels.
    """

    if not isinstance(text, str):
        return ""

    for pattern, replacement in _RULES:
        text = pattern.sub(replacement, text)

    return text
