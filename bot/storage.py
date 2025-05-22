import json
from typing import List, Dict, Any

FILE_PATH = "data.json"

def load_players(filename: str = FILE_PATH) -> List[Dict[str, Any]]:
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_to_json(chat_id: int, data: List[str]) -> bool:
    if len(data) < 8:
        raise ValueError("Недостаточно данных для регистрации игрока.")

    record = {
        "user_id": chat_id,
        "nickname": data[0].strip(),
        "alliance": data[1].strip(),
        "troop_type": data[2].strip(),
        "troop_size": data[3].strip(),
        "tier": data[4].strip().upper().replace("Т", "T"),
        "group_capacity": data[5].strip(),
        "shift": data[6].strip().lower(),
        "captain": data[7].strip().lower(),
        "true_power": data[8].strip() if len(data) > 8 else "0"
    }

    players = load_players()
    players = [p for p in players if p.get("nickname", "").strip().lower() != record["nickname"].lower()]
    players.append(record)

    with open(FILE_PATH, "w", encoding="utf-8") as file:
        json.dump(players, file, ensure_ascii=False, indent=2)

    return True

def update_player_by_nickname(nickname: str, field: str, new_value: Any) -> bool:
    players = load_players()
    updated = False
    nickname = nickname.strip().lower()

    for player in players:
        if player.get("nickname", "").strip().lower() == nickname:
            player[field] = new_value.strip() if isinstance(new_value, str) else new_value
            updated = True

    if updated:
        with open(FILE_PATH, "w", encoding="utf-8") as file:
            json.dump(players, file, ensure_ascii=False, indent=2)

    return updated

def delete_player_by_nickname(nickname: str) -> bool:
    players = load_players()
    nickname = nickname.strip().lower()
    new_players = [p for p in players if p.get("nickname", "").strip().lower() != nickname]

    if len(new_players) < len(players):
        with open(FILE_PATH, "w", encoding="utf-8") as file:
            json.dump(new_players, file, ensure_ascii=False, indent=2)
        return True

    return False
