from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from config import ADMINS
from shared import user_lang
from languages import questions
from storage import save_to_json, load_players
from utils import validate_troop_input, validate_tier, validate_power
import re
import random

user_answers = {}
(
    STEP_NICK, STEP_ALLIANCE, STEP_TYPE, STEP_SIZE,
    STEP_TIER, STEP_CAPACITY, STEP_SHIFT, STEP_CAPTAIN, STEP_POWER
) = range(9)

tips = {
    "ru": [
        "🌹 Надень щит во время ДЗ, чтобы сохранить ресурсы!",
        "🏠 Участвуй в защите башен, чтобы получить бонусы альянса.",
        "⚔️ Размещай юниты соответствующего типа в башне.",
        "📦 Проверь вместимость своих отрядов перед событием.",
        "⏰ Не забудь про смену по времени — будь онлайн заранее!"
    ]
}

async def registration_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = user_lang.get(chat_id, "ru")
    user_answers[chat_id] = []
    await (update.callback_query.message if update.callback_query else update.message).reply_text(questions[lang][0])
    return STEP_NICK

async def collect_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = user_lang.get(chat_id, "ru")
    text = update.message.text.strip()
    step = len(user_answers.get(chat_id, []))

    if not text:
        await update.message.reply_text("Поле обязательно.")
        return step

    if step == STEP_NICK:
        if any(p["nickname"].strip().lower() == text.lower() for p in load_players()):
            await update.message.reply_text("⛔ Такой ник уже зарегистрирован.")
            return STEP_NICK

    if step == STEP_ALLIANCE and (re.search(r"[А-Яа-яЁё]", text) or len(text) != 3):
        await update.message.reply_text("Альянс: латиница, 3 буквы.")
        return STEP_ALLIANCE

    if step == STEP_SIZE and not validate_troop_input(text):
        await update.message.reply_text("Отряд: число от 200000 до 700000.")
        return STEP_SIZE

    if step == STEP_TIER and not validate_tier(text):
        await update.message.reply_text("Тир должен быть от T10 до T13.")
        return STEP_TIER

    if step == STEP_CAPACITY and not validate_troop_input(text):
        await update.message.reply_text("Группа: число от 800000 до 3.500.000.")
        return STEP_CAPACITY

    if step == STEP_POWER:
        if not validate_power(text) or int(text) < 300_000_000:
            await update.message.reply_text("Укажи свою **личную мощь** числом от 300.000.000 и выше:")
            return STEP_POWER
        user_answers[chat_id].append(text)
        save_to_json(chat_id, user_answers[chat_id])
        await update.message.reply_text("✅ Готово!\n" + random.choice(tips[lang]))
        return ConversationHandler.END

    user_answers[chat_id].append(text)
    step += 1

    if step == STEP_TYPE:
        return await send_troop_type_buttons(update, lang)
    elif step == STEP_SHIFT:
        return await send_shift_buttons(update, lang)
    elif step == STEP_CAPTAIN:
        return await send_captain_buttons(update, lang)
    elif step < len(questions[lang]):
        await update.message.reply_text(questions[lang][step])
        return step

    save_to_json(chat_id, user_answers[chat_id])
    await update.message.reply_text("✅ Готово!\n" + random.choice(tips[lang]))
    return ConversationHandler.END

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    lang = user_lang.get(chat_id, "ru")
    step = len(user_answers.get(chat_id, []))
    data = query.data

    if step == STEP_TYPE:
        user_answers[chat_id].append(data)
        await query.message.reply_text(questions[lang][STEP_SIZE])
        return STEP_SIZE

    elif step == STEP_SHIFT:
        user_answers[chat_id].append(data)
        return await send_captain_buttons(update, lang)

    elif step == STEP_CAPTAIN:
        user_answers[chat_id].append(data)
        if data.lower() == "да":
            await query.message.reply_text("Укажи свою **личную мощь** (от 300.000.000):")
            return STEP_POWER
        else:
            user_answers[chat_id].append("0")
            save_to_json(chat_id, user_answers[chat_id])
            await query.message.reply_text("✅ Готово!\n" + random.choice(tips[lang]))
            return ConversationHandler.END

    return ConversationHandler.END

async def send_troop_type_buttons(update, lang):
    options = {"ru": ["байкер", "боец", "стрелок"]}
    buttons = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in options[lang]]
    await update.message.reply_text(questions[lang][STEP_TYPE], reply_markup=InlineKeyboardMarkup(buttons))
    return STEP_TYPE

async def send_shift_buttons(update, lang):
    options = {"ru": ["1", "2", "обе"]}
    buttons = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in options[lang]]
    await (update.callback_query.message if update.callback_query else update.message).reply_text(
        questions[lang][STEP_SHIFT], reply_markup=InlineKeyboardMarkup(buttons)
    )
    return STEP_SHIFT

async def send_captain_buttons(update, lang):
    options = {"ru": ["да", "нет"]}
    buttons = [[InlineKeyboardButton(opt, callback_data=opt)] for opt in options[lang]]
    await (update.callback_query.message if update.callback_query else update.message).reply_text(
        questions[lang][STEP_CAPTAIN], reply_markup=InlineKeyboardMarkup(buttons)
    )
    return STEP_CAPTAIN

def get_registration_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("register", registration_start),
            MessageHandler(filters.Regex("Регистрация"), registration_start)
        ],
        states={
            STEP_NICK: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_answer)],
            STEP_ALLIANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_answer)],
            STEP_TYPE: [CallbackQueryHandler(handle_button)],
            STEP_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_answer)],
            STEP_TIER: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_answer)],
            STEP_CAPACITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_answer)],
            STEP_SHIFT: [CallbackQueryHandler(handle_button)],
            STEP_CAPTAIN: [CallbackQueryHandler(handle_button)],
            STEP_POWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_answer)],
        },
        fallbacks=[]
    )
