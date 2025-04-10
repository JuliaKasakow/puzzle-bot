import re

def parse_capacity(value):
    # Удаляем точки, заменяем запятые на точки, затем пытаемся преобразовать в число
    value = value.replace(".", "").replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return 0.0

def tier_priority(tier):
    # Преобразуем Т9 / T9 → 9
    tier = str(tier).upper().replace("Т", "T")
    match = re.search(r"T(\d+)", tier)
    return int(match.group(1)) if match else 0

def validate_troop_input(value):
    # Новая проверка: не менее 6 цифр подряд, без обязательного формата
    digits_only = re.sub(r"\D", "", value)
    return len(digits_only) >= 6
