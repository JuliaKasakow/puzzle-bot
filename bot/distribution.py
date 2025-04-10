import json
import re

FILE_PATH = "data.json"

def parse_capacity(value):
    try:
        return float(value.replace(".", "").replace(",", "."))
    except:
        return 0.0

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
        shift = str(p.get("shift", "1"))
        if shift in shifts:
            shifts[shift].append(p)
        elif shift.lower() in ["both", "обе", "beide"]:
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

def distribute_by_troop(players):
    towers = {"байкер": [], "боец": [], "стрелок": []}
    for p in players:
        t = p.get("troop_type", "").lower()
        for key in towers:
            if key in t:
                towers[key].append(p)
                break
    return towers

def sort_players(players):
    return sorted(
        players,
        key=lambda p: (-tier_priority(p.get("tier", "")), -parse_capacity(p.get("group_capacity", "0")))
    )

def assign_to_captain_group(players):
    players = sort_players(players)
    result = []
    remaining = players.copy()

    while remaining:
        captains = [p for p in remaining if p.get("captain", "").lower() in ["да", "yes", "ja"]]
        if not captains:
            captains = remaining

        captain = max(captains, key=lambda p: parse_capacity(p.get("group_capacity", "0")))
        group_capacity = parse_capacity(captain.get("group_capacity", "0"))
        assigned = [{"nickname": captain["nickname"], "alliance": captain["alliance"], "as_captain": True, "used": 0, "max": group_capacity}]
        remaining.remove(captain)

        used = 0
        sorted_remaining = sort_players(remaining)

        for p in sorted_remaining:
            size = parse_capacity(p.get("troop_size", "0"))
            space_left = group_capacity - used
            if space_left <= 0:
                break
            if size <= space_left:
                assigned.append({"nickname": p["nickname"], "alliance": p["alliance"], "used": size, "max": size})
                used += size
                remaining.remove(p)
            else:
                assigned.append({"nickname": p["nickname"], "alliance": p["alliance"], "used": space_left, "max": size})
                used += space_left
                remaining.remove(p)

        result.append({"captain": captain["nickname"], "members": assigned})

    return result

def format_tower_output(tower_name, players):
    output = [f"{tower_name.capitalize()}"]
    groups = assign_to_captain_group(players)
    for group in groups:
        output.append(f"\nКапитан: {group['captain']}")
        for m in group["members"]:
            if m.get("as_captain"):
                output.append(f"{m['nickname']} [{m['alliance']}] (капитан) — вместимость: {m['max']:.0f}")
            else:
                output.append(f"{m['nickname']} [{m['alliance']}] — вводит: {m['used']:.0f} из {m['max']:.0f}")
    return "\n".join(output)

def get_hub_group(players):
    best = max(players, key=lambda p: (tier_priority(p["tier"]), parse_capacity(p["group_capacity"])))
    troop_type = best["troop_type"]
    same_type = [p for p in players if p["troop_type"] == troop_type]
    return format_tower_output("Хаб", same_type)

def generate_distribution(filename=FILE_PATH):
    all_players = load_players(filename)
    shift_groups = balance_shifts(group_by_shift(all_players))
    result = []

    for shift, players in shift_groups.items():
        result.append(f"Смена {shift}")
        result.append(get_hub_group(players))
        towers = distribute_by_troop(players)
        used_types = set(towers.keys())
        for name in used_types:
            result.append(format_tower_output(f"Башня {name}", towers[name]))

        # Добавим башню "Микс", если остались игроки не попавшие в основные
        all_assigned = sum([towers[k] for k in used_types], [])
        leftovers = [p for p in players if p not in all_assigned]
        if leftovers:
            result.append(format_tower_output("Башня микс", leftovers))

    return "\n\n".join(result)

if __name__ == "__main__":
    print(generate_distribution())
