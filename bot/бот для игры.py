from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)
from shared import user_lang
from handlers import get_registration_handler, registration_start
from distribution import generate_distribution
from storage import update_player_by_nickname
import logging
import json
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMINS = [5281668146, 1739936136]  # Список ID администраторов
LANG_SELECT = 0

# Постоянные кнопки
main_keyboard_user = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton("📝 Регистрация"), KeyboardButton("📋 Список")]],
    resize_keyboard=True
)

main_keyboard_admin = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("📝 Регистрация"), KeyboardButton("📋 Список")],
        [KeyboardButton("/finish"), KeyboardButton("/distribute")],
        [KeyboardButton("/edit"), KeyboardButton("/reset")]
    ],
    resize_keyboard=True
)

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
        return await registration_callback(update, context)
    elif "Список" in text:
        await show_list(update, context)

async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("data.json", "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        await update.message.reply_text("Список пуст. Никто ещё не зарегистрировался.")
        return

    if not isinstance(data, list) or not data:
        await update.message.reply_text("Список пуст.")
        return

    lines = []
    alliance_count = {}

    for player in data:
        nick = player.get("nickname")
        alliance = player.get("alliance")
        if nick and alliance:
            lines.append(f"{nick} | {alliance}")
            tag = alliance.upper()
            alliance_count[tag] = alliance_count.get(tag, 0) + 1

    result = "Зарегистрированные участники:\n" + "\n".join(lines)
    result += "\n\nУчастники по альянсам:"
    for tag, count in sorted(alliance_count.items(), key=lambda x: (-x[1], x[0])):
        result += f"\n{tag}: {count}"

    await update.message.reply_text(result)

async def finish_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("⛔ У вас нет прав на эту команду.")
        return
    await update.message.reply_text("✅ Регистрация завершена. Расчёт башен будет добавлен позже.")

async def reset_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("⛔ У вас нет прав на эту команду.")
        return

    if os.path.exists("data.json"):
        os.remove("data.json")
        await update.message.reply_text("🗑 Регистрация сброшена.")
    else:
        await update.message.reply_text("Файл уже пуст.")

async def registration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await registration_start(update, context)

async def run_distribution(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("⛔ У вас нет прав на эту команду.")
        return

    await update.message.reply_text("📊 Распределение по башням:")
    result = generate_distribution("data.json")
    for block in result.split("\n\n"):
        if block.strip():
            await update.message.reply_text(block.strip())

async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("⛔ У вас нет прав на эту команду.")
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Использование: /edit <ник> <поле> <новое_значение>")
        return

    nickname = args[0]
    field = args[1]
    new_value = " ".join(args[2:])

    if update_player_by_nickname(nickname, field, new_value):
        await update.message.reply_text(f"✅ Обновлено: {field} у {nickname} теперь {new_value}")
    else:
        await update.message.reply_text("❌ Не удалось найти игрока с таким ником или поле указано неверно.")

async def show_my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"Ваш user_id: {user_id}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    app = ApplicationBuilder().token(TOKEN).connect_timeout(10).read_timeout(10).build()

    lang_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={LANG_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_language)]},
        fallbacks=[],
    )

    app.add_handler(lang_handler)
    app.add_handler(get_registration_handler())
    app.add_handler(CommandHandler("id", show_my_id))
    app.add_handler(CommandHandler("finish", finish_registration))
    app.add_handler(CommandHandler("reset", reset_registration))
    app.add_handler(CommandHandler("distribute", run_distribution))
    app.add_handler(CommandHandler("edit", edit_field))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_buttons))

    app.run_polling()