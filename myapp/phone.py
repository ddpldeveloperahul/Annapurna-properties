import re


def normalize_indian_mobile(raw_number: str) -> str:
    """Normalize a raw caller-id / user-entered number to E.164-ish
    "+91XXXXXXXXXX" form so the same customer always maps to one lead,
    regardless of how the number arrived (with spaces, a leading 0, no
    country code, etc). This backs the SOW's duplicate-number rule.
    """
    if not raw_number:
        return raw_number
    digits = re.sub(r"\D", "", raw_number)
    if digits.startswith("0091"):
        digits = digits[4:]
    if digits.startswith("91") and len(digits) == 12:
        pass
    elif digits.startswith("0") and len(digits) == 11:
        digits = "91" + digits[1:]
    elif len(digits) == 10:
        digits = "91" + digits
    return f"+{digits}"
