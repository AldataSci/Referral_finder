"""ZIP and phone normalization."""
import re


def zip5(value: str | None) -> str | None:
    """NPI stores ZIPs as 5 or 9 digits without a hyphen; keep the first 5."""
    digits = re.sub(r"\D", "", value or "")
    return digits[:5] if len(digits) >= 5 else None


def phone10(value: str | None) -> str | None:
    """10-digit US phone, or None if it isn't one."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits if len(digits) == 10 else None
