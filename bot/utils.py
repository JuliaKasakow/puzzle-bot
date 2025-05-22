import re

def parse_capacity(value):
    try:
        value = str(value).replace(".", "").replace(",", "")
        return int(value)
    except (ValueError, AttributeError):
        return 0

def tier_priority(tier):
    tier = str(tier).upper().replace("Т", "T")
    match = re.search(r"T(\d+)", tier)
    return int(match.group(1)) if match else 0

def validate_troop_input(value):
    try:
        number = int(re.sub(r"\D", "", str(value)))
        return 200_000 <= number <= 700_000 or 800_000 <= number <= 3_500_000
    except (ValueError, TypeError):
        return False

def validate_tier(tier):
    tier = str(tier).upper().replace("Т", "T")
    return tier in {"T10", "T11", "T12", "T13"}

def validate_shift(shift):
    shift = str(shift).strip().lower()
    return shift in {"1", "2", "обе", "both", "beide"}

def validate_power(value):
    try:
        number = int(re.sub(r"\D", "", str(value)))
        return number >= 300_000_000
    except (ValueError, TypeError):
        return False
