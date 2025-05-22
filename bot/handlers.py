from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from config import ADMINS
from storage import load_players, update_player_by_nickname, delete_player_by_nickname
from utils import validate_troop_input, validate_tier, validate_shift, validate_power

EDIT_SELECT_PLAYER, EDIT_SELECT_FIELD, EDIT_ENTER_VALUE, EDIT_CONFIRM_DELETE = range(9, 13)

def is_admin(user_id):
    return user_id in ADMINS

async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ У вас нет прав.")
        return

    players = load_players()
    if not players:
        await update.message.reply_text("Список пуст.")
        return

    buttons = [[InlineKeyboardButton(p['nickname'], callback_data=f"edit_nick|{p['nickname']}")] for p in players]
    await update.message.reply_text("Выберите участника:", reply_markup=InlineKeyboardMarkup(buttons))
    return EDIT_SELECT_PLAYER

async def edit_player_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    await update.callback_query.answer()
    _, nickname = update.callback_query.data.split("|")
    context.user_data["edit_nick"] = nickname

    fields = ["nickname", "alliance", "troop_type", "troop_size", "tier", "group_capacity", "shift", "captain", "true_power"]
    buttons = [[InlineKeyboardButton(field, callback_data=f"edit_field|{field}")] for field in fields]
    buttons.append([InlineKeyboardButton("❌ Удалить", callback_data="delete_user")])

    await update.callback_query.edit_message_text("Выберите поле для изменения или удалите:", reply_markup=InlineKeyboardMarkup(buttons))
    return EDIT_SELECT_FIELD

async def edit_field_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.callback_query.answer()
    _, field = update.callback_query.data.split("|")
    context.user_data["edit_field"] = field
    await update.callback_query.edit_message_text(f"Введите новое значение для {field}:")
    return EDIT_ENTER_VALUE

async def apply_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = context.user_data["edit_nick"]
    field = context.user_data["edit_field"]
    value = update.message.text.strip()

    if field == "troop_size" and not validate_troop_input(value):
        await update.message.reply_text("❌ Отряд: число от 200000 до 700000.")
        return EDIT_ENTER_VALUE

    if field == "tier" and not validate_tier(value):
        await update.message.reply_text("❌ Тир должен быть от T10 до T13.")
        return EDIT_ENTER_VALUE

    if field == "group_capacity" and not validate_troop_input(value):
        await update.message.reply_text("❌ Группа: число от 800000 до 3.500.000.")
        return EDIT_ENTER_VALUE

    if field == "shift" and not validate_shift(value):
        await update.message.reply_text("❌ Смена должна быть 1, 2 или обе.")
        return EDIT_ENTER_VALUE

    if field == "true_power":
        if not validate_power(value) or int(value) < 300_000_000:
            await update.message.reply_text("❌ Личная мощь должна быть числом от 300.000.000.")
            return EDIT_ENTER_VALUE

    if update_player_by_nickname(nickname, field, value):
        await update.message.reply_text(f"✅ Обновлено: {nickname}.{field} = {value}")
    else:
        await update.message.reply_text("❌ Не удалось изменить.")
    return ConversationHandler.END

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Удалить участника?", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Да", callback_data="delete_confirm")],
        [InlineKeyboardButton("Отмена", callback_data="delete_cancel")]
    ]))
    return EDIT_CONFIRM_DELETE

async def delete_user_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.callback_query.answer()
    nickname = context.user_data["edit_nick"]
    delete_player_by_nickname(nickname)
    await update.callback_query.edit_message_text(f"🗑 Участник {nickname} удалён.")
    return ConversationHandler.END

async def delete_user_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Удаление отменено.")
    return ConversationHandler.END

def get_edit_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("edit", edit_command),
            MessageHandler(filters.Regex("Список"), edit_command)
        ],
        states={
            EDIT_SELECT_PLAYER: [CallbackQueryHandler(edit_player_callback, pattern="^edit_nick\\|")],
            EDIT_SELECT_FIELD: [
                CallbackQueryHandler(edit_field_callback, pattern="^edit_field\\|"),
                CallbackQueryHandler(confirm_delete, pattern="^delete_user$")
            ],
            EDIT_ENTER_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_edit)],
            EDIT_CONFIRM_DELETE: [
                CallbackQueryHandler(delete_user_confirm, pattern="^delete_confirm$"),
                CallbackQueryHandler(delete_user_cancel, pattern="^delete_cancel$")
            ]
        },
        fallbacks=[]
    )
