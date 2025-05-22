from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from shared import user_lang
from registration import get_registration_handler
from handlers import get_edit_conversation_handler
from distribution import generate_distribution
from sheets_importer import sync_from_google
from storage import load_players
from config import ADMINS
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import os

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
LANG_SELECT = 0

main_keyboard_user = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton("📝 Регистрация"), KeyboardButton("📋 Список (короткий)")]],
    resize_keyboard=True
)

main_keyboard_admin = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("📝 Регистрация"), KeyboardButton("📋 Список"), KeyboardButton("📋 Список (короткий)")],
        [KeyboardButton("/finish"), KeyboardButton("/distribute")],
        [KeyboardButton("/edit"), KeyboardButton("/reset"), KeyboardButton("/sync")]
    ],
    resize_keyboard=True
)

def split_text(text, limit=4000):
    lines = text.split('\n')
    chunks = []
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 < limit:
            current += line + "\n"
        else:
            chunks.append(current.strip())
            current = line + "\n"
    if current:
        chunks.append(current.strip())
    return chunks

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите язык / Wähle Sprache / Choose language:",
        reply_markup=ReplyKeyboardMarkup(
            [["Русский 🇷🇺", "Deutsch 🇩🇪", "English 🇬🇧"]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return LANG_SELECT

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text

    if "Русский" in text:
        user_lang[chat_id] = "ru"
        reply_kb = main_keyboard_admin if user_id in ADMINS else main_keyboard_user
        await update.message.reply_text("Язык установлен: Русский 🇷🇺", reply_markup=reply_kb)
    elif "Deutsch" in text:
        user_lang[chat_id] = "de"
        reply_kb = main_keyboard_admin if user_id in ADMINS else main_keyboard_user
        await update.message.reply_text("Sprache eingestellt: Deutsch 🇩🇪", reply_markup=reply_kb)
    elif "English" in text:
        user_lang[chat_id] = "en"
        reply_kb = main_keyboard_admin if user_id in ADMINS else main_keyboard_user
        await update.message.reply_text("Language set: English 🇬🇧", reply_markup=reply_kb)
    else:
        await update.message.reply_text("Пожалуйста, выберите язык с помощью кнопки.")
        return LANG_SELECT

    return ConversationHandler.END

async def handle_main_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "Регистрация" in text:
        from registration import registration_start
        return await registration_start(update, context)
    elif "Список (короткий)" in text:
        await show_short_list(update)
    elif "Список" in text:
        await show_full_list(update)

async def show_full_list(update: Update):
    user_id = update.effective_user.id
    is_admin = user_id in ADMINS
    try:
        data = load_players()
    except FileNotFoundError:
        await update.message.reply_text("Список пуст.")
        return
    if not data:
        await update.message.reply_text("Список пуст.")
        return

    lines = [
        f"{p['nickname']} | {p['alliance']} | {p['troop_type']} | {p['troop_size']} | tier {p['tier']} | shift {p['shift']} | cap: {p['captain']} | group: {p['group_capacity']}"
        for p in data
    ] if is_admin else [f"{p['nickname']} | {p['alliance']}" for p in data]

    result = "Участники:\n" + "\n".join(lines)
    for chunk in split_text(result):
        await update.message.reply_text(chunk)

async def show_short_list(update: Update):
    try:
        data = load_players()
    except FileNotFoundError:
        await update.message.reply_text("Список пуст.")
        return
    if not data:
        await update.message.reply_text("Список пуст.")
        return

    lines = [f"{p['nickname']} | {p['alliance']}" for p in data]
    alliance_count = {}
    for p in data:
        tag = p.get("alliance", "").upper()
        alliance_count[tag] = alliance_count.get(tag, 0) + 1

    result = f"Участники ({len(data)}):\n" + "\n".join(lines) + "\n\nПо альянсам:"
    for tag, count in sorted(alliance_count.items(), key=lambda x: -x[1]):
        result += f"\n{tag}: {count}"

    for chunk in split_text(result):
        await update.message.reply_text(chunk)

async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("⛔ Нет прав.")
        return
    await update.message.reply_text("✅ Регистрация завершена.")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("⛔ Нет прав.")
        return
    if os.path.exists("data.json"):
        os.remove("data.json")
        await update.message.reply_text("🗑 Сброшено.")
    else:
        await update.message.reply_text("Файл пуст.")

async def distribute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("⛔ Нет прав.")
        return
    await update.message.reply_text("📊 Распределение:")
    try:
        result = generate_distribution()
        for chunk in split_text(result):
            await update.message.reply_text(chunk)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при распределении: {e}")

async def sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("⛔ Нет прав.")
        return
    await update.message.reply_text("🔄 Загружаю данные из Google Таблицы...")
    count = sync_from_google()
    await update.message.reply_text(f"✅ Загружено записей: {count}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(sync_from_google, 'interval', hours=1)
    scheduler.start()
    logging.info("⏰ Планировщик запущен: Google Sheets будут синхронизироваться каждый час.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={LANG_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_language)]},
        fallbacks=[],
    ))

    app.add_handler(get_registration_handler())
    app.add_handler(get_edit_conversation_handler())
    app.add_handler(CommandHandler("finish", finish))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("distribute", distribute))
    app.add_handler(CommandHandler("sync", sync))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_buttons))

    start_scheduler()
    app.run_polling()
