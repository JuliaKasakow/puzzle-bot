# google_sync.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from storage import save_to_json, load_players

SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = 'creds.json'
SPREADSHEET_ID = "1Cm1i7fScmBEPbn8tN8i12gbb2-aIwfv83Sh2SwTW8g4"

REQUIRED_FIELDS = [
    'nickname', 'alliance', 'troop_type',
    'troop_size', 'tier', 'group_capacity',
    'shift', 'captain', 'true_power'
]

def sync_from_google():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    data = sheet.get_all_records()

    existing = load_players()
    existing_nicks = {p['nickname'].strip().lower() for p in existing}

    added = 0
    for row in data:
        nick = row.get('nickname', '').strip()
        if not nick or nick.lower() in existing_nicks:
            continue

        if not all(field in row and str(row[field]).strip() for field in REQUIRED_FIELDS):
            print(f"⚠️ Пропущены обязательные поля в строке: {row}")
            continue

        try:
            record = [
                row['nickname'].strip(),
                row['alliance'].strip(),
                row['troop_type'].strip(),
                str(row['troop_size']).strip(),
                row['tier'].strip().upper().replace("Т", "T"),
                str(row['group_capacity']).strip(),
                row['shift'].strip().lower(),
                row['captain'].strip().lower(),
                str(row['true_power']).strip()
            ]
            save_to_json(row.get('user_id', 0), record)
            added += 1
        except Exception as e:
            print(f"❌ Ошибка при импорте строки {row}: {e}")

    print(f"✅ Импорт завершён. Добавлено участников: {added}")
    return added
