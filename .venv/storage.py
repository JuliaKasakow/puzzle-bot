import json
import os

FILE_PATH = "data.json"

def save_to_json(chat_id, data):
    record = {
        "user_id": chat_id,
        "nickname": data[0],
        "alliance": data[1],
        "troop_type": data[2],
        "troop_size": data[3],
        "tier": data[4],
        "group_capacity": data[5],
        "shift": data[6],
        "captain": data[7]
    }

    all_data = load_players()

    # Перезапись по нику
    all_data = [p for p in all_data if p["nickname"].lower() != record["nickname"].lower()]
    all_data.append(record)

    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

def load_players(filename=FILE_PATH):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def update_player_by_nickname(nickname, field, new_value):
    all_data = load_players()
    updated = False
    for player in all_data:
        if player["nickname"].lower() == nickname.lower():
            if field in player:
                player[field] = new_value
                updated = True
    if updated:
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
    return updated
