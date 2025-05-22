import json
import re

FILE_PATH = "data.json"

def parse_capacity(value):
    try:
        value = str(value).replace(" ", "").replace(".", "").replace(",", "")
        return int(value)
    except (ValueError, TypeError):
        return 0

def tier_priority(tier):
    tier = str(tier).upper().replace("Т", "T")
    match = re.search(r"T(\d+)", tier)
    return int(match.group(1)) if match else 0

def load_players(filename=FILE_PATH):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def group_by_shift(players):
    shifts = {"1": [], "2": [], "обе": []}
    for p in players:
        shift = str(p.get("shift", "1")).lower()
        if shift in ["1", "2"]:
            shifts[shift].append(p)
        elif shift in ["both", "обе", "beide"]:
            shifts["обе"].append(p)
    return shifts

def balance_shifts(shifted):
    shift1 = shifted["1"]
    shift2 = shifted["2"]
    both = shifted["обе"]
    for player in both:
        if len(shift1) <= len(shift2):
            shift1.append(player)
        else:
            shift2.append(player)
    return {"1": shift1, "2": shift2}

def sort_players(players):
    return sorted(
        players,
        key=lambda p: (-tier_priority(p.get("tier", "")), -parse_capacity(p.get("group_capacity", "0")))
    )

def assign_captains(players):
    candidates = [
        p for p in players
        if p.get("captain", "").lower() == "да"
        and parse_capacity(p.get("true_power", "0")) >= 300_000_000
    ]
    if len(candidates) < 5:
        candidates = players

    def sort_key(p):
        return (
            -parse_capacity(p.get("true_power", "0")),
            -tier_priority(p.get("tier", "")),
            -parse_capacity(p.get("group_capacity", "0"))
        )

    sorted_candidates = sorted(candidates, key=sort_key)
    selected = []
    used = set()
    for p in sorted_candidates:
        if p["nickname"] not in used:
            selected.append(p)
            used.add(p["nickname"])
        if len(selected) == 5:
            break
    return selected

def assign_to_tower(captain, players, allowed_type=None, assigned_nicks=None):
    if assigned_nicks is None:
        assigned_nicks = set()

    group_capacity = parse_capacity(captain.get("group_capacity", "0"))
    if group_capacity == 0:
        return []

    assigned = []
    remaining = [p for p in players if p["nickname"] not in assigned_nicks and p["nickname"] != captain["nickname"]]

    if allowed_type:
        remaining = [p for p in remaining if allowed_type == p.get("troop_type", "").lower()]

    remaining = sorted(
        remaining,
        key=lambda p: (-tier_priority(p.get("tier", "")), -parse_capacity(p.get("troop_size", "0")))
    )

    used = 0
    for p in remaining:
        if used >= group_capacity:
            break
        size = parse_capacity(p.get("troop_size", "0"))
        fit_size = min(size, group_capacity - used)
        p_copy = p.copy()
        p_copy["assigned"] = fit_size
        assigned.append(p_copy)
        assigned_nicks.add(p["nickname"])
        used += fit_size

    assigned_nicks.add(captain["nickname"])
    return assigned

def format_tower(title, captain, members):
    alliance = captain.get("alliance", "").upper()
    lines = [
        f"{title}",
        f"Капитан: {captain['nickname']} [{alliance}] вместимость: {parse_capacity(captain['group_capacity']):,}".replace(",", " ")
    ]
    for m in members:
        if "assigned" in m:
            lines.append(f"{m['nickname']} [{m.get('alliance', '').upper()}] — {int(m['assigned']):,}".replace(",", " "))
    return "\n".join(lines)

def generate_distribution(filename=FILE_PATH):
    players = load_players(filename)
    shifts = balance_shifts(group_by_shift(players))
    result = []

    for shift, shift_players in shifts.items():
        result.append(f"\n🕐 Смена {shift}")
        shift_players = sort_players(shift_players)
        captains = assign_captains(shift_players)

        if len(captains) < 5:
            result.append("❗ Недостаточно капитанов!")
            continue

        assigned_nicks = set(p["nickname"] for p in captains)

        # Хаб
        hub_captain = captains[0]
        hub_type = hub_captain.get("troop_type", "").lower()
        hub_members = assign_to_tower(hub_captain, shift_players, allowed_type=hub_type, assigned_nicks=assigned_nicks)
        result.append(format_tower("🏠 Хаб (лучшие бойцы)", hub_captain, hub_members))

        # Башни по типу
        for i, troop_type in enumerate(["стрелок", "байкер", "боец"], start=1):
            cap = captains[i]
            members = assign_to_tower(cap, shift_players, allowed_type=troop_type, assigned_nicks=assigned_nicks)
            result.append(format_tower(f"🛡 Башня {troop_type}", cap, members))

        # Микс
        mix_captain = captains[4]
        mix_members = assign_to_tower(mix_captain, shift_players, assigned_nicks=assigned_nicks)
        result.append(format_tower("⚔️ Башня микс", mix_captain, mix_members))

    return "\n\n".join(result)

if __name__ == "__main__":
    print(generate_distribution())
