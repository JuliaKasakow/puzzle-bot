from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from shared import user_lang
from languages import questions
from storage import save_to_json
from utils import validate_troop_input
import random
import re

user_answers = {}

(
    STEP_NICK, STEP_ALLIANCE, STEP_TYPE, STEP_SIZE,
    STEP_TIER, STEP_CAPACITY, STEP_SHIFT, STEP_CAPTAIN
) = range(8)

tips = {
    "ru": [
        "🛡 Надень щит во время ДЗ, чтобы сохранить ресурсы!",
        "🏰 Участвуй в защите башен, чтобы получить бонусы альянса.",
        "⚔️ Размещай юниты соответствующего типа в башне.",
        "📦 Проверь вместимость своих отрядов перед событием.",
        "⏰ Не забудь про смену по времени — будь онлайн заранее!",
        "👑 Король Пустоши требует координации — пиши в альянс-чате!",
        "🚫 Если не можешь участвовать — предупреди и не занимай слот.",
        "💬 Назначай капитанов заранее, чтобы избежать путаницы.",
        "🧪 Усиливай отряд баффами перед битвой за башню.",
        "🔄 Проверяй свою смену и тип войск — не перепутай!",
        "📦 Вскрывай ящики под ивенты — получишь больше наград.",
        "🧱 Не храни ресурсы на стене — их легко потерять.",
        "🕊 Если вышел на плитку одновременно с врагом — надень щит!",
        "⛏ Не собирай ресурсы в грязи во время Пустоши — это опасно.",
        "🛑 Не пиши в боевом дивизионе до договора о НАП.",
        "⚠️ Не атакуй чужие башни до договора о НАП.",
        "🚫 Нападения на башни в своём регионе запрещены.",
        "🏕 Не ставь свою штаб-квартиру на грязь — это опасно."
    ],
    "en": [],
    "de": []
}

# Старт регистрации
async def registration_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = user_lang.get(chat_id, "ru")
    user_answers[chat_id] = []

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(questions[lang][0])
    else:
        await update.message.reply_text(questions[lang][0])

    return STEP_NICK

# Ответы текстом
async def collect_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang = user_lang.get(chat_id, "ru")
    text = update.message.text.strip()
    step = len(user_answers.get(chat_id, []))

    if not text:
        await update.message.reply_text({
            "ru": "Это поле обязательно. Пожалуйста, введите ответ.",
            "de": "Dieses Feld ist erforderlich. Bitte gib eine Antwort ein.",
            "en": "This field is required. Please provide an answer."
        }[lang])
        return step

    if step == STEP_ALLIANCE:
        if re.search(r"[А-Яа-яЁё]", text):
            await update.message.reply_text({
                "ru": "Название альянса должно быть на латинице (без кириллицы).",
                "de": "Der Allianzname darf keine kyrillischen Buchstaben enthalten.",
                "en": "Alliance name must not contain Cyrillic letters."
            }[lang])
            return step

    if step in [STEP_SIZE, STEP_CAPACITY]:
        if not validate_troop_input(text):
            await update.message.reply_text({
                "ru": "Введите значение числом не менее 6 знаков, например: 456000",
                "de": "Bitte gib eine Zahl mit mindestens 6 Zeichen ein, z. B.: 456000",
                "en": "Enter a number with at least 6 characters, e.g.: 456000"
            }[lang])
            return step

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
    else:
        save_to_json(chat_id, user_answers[chat_id])
        await update.message.reply_text(get_thank_you(lang))
        await update.message.reply_text(random.choice(tips[lang]))
        return ConversationHandler.END

# Обработка кнопок
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    lang = user_lang.get(chat_id, "ru")
    await query.answer()

    user_answers.setdefault(chat_id, []).append(query.data)
    step = len(user_answers[chat_id])

    if step == STEP_SHIFT:
        return await send_shift_buttons(update, lang)
    elif step == STEP_CAPTAIN:
        return await send_captain_buttons(update, lang)
    elif step < len(questions[lang]):
        await query.message.reply_text(questions[lang][step])
        return step
    else:
        save_to_json(chat_id, user_answers[chat_id])
        await query.message.reply_text(get_thank_you(lang))
        await query.message.reply_text(random.choice(tips[lang]))
        return ConversationHandler.END

# Благодарность

def get_thank_you(lang):
    return {
        "ru": "Спасибо! Вы зарегистрированы. 👍",
        "de": "Danke! Du bist angemeldet. 👍",
        "en": "Thank you! You are registered. 👍"
    }[lang]

# Кнопки — тип войск
async def send_troop_type_buttons(update, lang):
    options = {
        "ru": ["байкер", "боец", "стрелок"],
        "de": ["Biker", "Kämpfer", "Schütze"],
        "en": ["biker", "fighter", "shooter"]
    }
    buttons = [[InlineKeyboardButton(text=opt, callback_data=opt)] for opt in options[lang]]
    await update.message.reply_text(
        questions[lang][STEP_TYPE],
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return STEP_TYPE

# Кнопки — смена
async def send_shift_buttons(update, lang):
    options = {
        "ru": ["1", "2", "обе"],
        "de": ["1", "2", "beide"],
        "en": ["1", "2", "both"]
    }
    buttons = [[InlineKeyboardButton(text=opt, callback_data=opt)] for opt in options[lang]]
    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text(
        questions[lang][STEP_SHIFT],
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return STEP_SHIFT

# Кнопки — капитан
async def send_captain_buttons(update, lang):
    options = {
        "ru": ["да", "нет"],
        "de": ["ja", "nein"],
        "en": ["yes", "no"]
    }
    buttons = [[InlineKeyboardButton(text=opt, callback_data=opt)] for opt in options[lang]]
    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text(
        questions[lang][STEP_CAPTAIN],
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return STEP_CAPTAIN

# Handler

def get_registration_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("register", registration_start),
            CallbackQueryHandler(registration_start, pattern="^start_registration$"),
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
        },
        fallbacks=[]
    )