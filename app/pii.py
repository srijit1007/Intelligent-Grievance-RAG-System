import re

_RULES = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[CARD]"),
    (re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b"), "[ID]"),      # Aadhaar-style
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[PAN]"),
    (re.compile(r"(?<!\w)\+?\d[\d -]{8,14}\d\b"), "[PHONE]"),
]


def redact(text: str) -> str:
    for rx, tag in _RULES:
        text = rx.sub(tag, text)
    return text
