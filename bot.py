import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler,
    ContextTypes, filters
)

# Состояния
LOGIN_ACCOUNT, LOGIN_PASSWORD, LOGIN_PIN, MENU = range(4)
TRANSFER_ACCOUNT, TRANSFER_AMOUNT, TRANSFER_CONFIRM = range(4, 7)

# Условная БД
users_db = {
    "BOM0": {"password": "zxcvBnm5", "pin": "0678", "balance": 1175, "user_id": None},
    "BOMNoName1042": {"password": "abobus2021", "pin": "2010", "balance": 1700, "user_id": None},
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("account"):
        return await show_menu(update, context)
    await update.message.reply_text("🔐 Введите номер счёта:")
    return LOGIN_ACCOUNT

async def login_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acc = update.message.text.strip()
    if acc not in users_db:
        await update.message.reply_text("❌ Счёт не найден. Попробуйте ещё:")
        return LOGIN_ACCOUNT
    context.user_data["account"] = acc
    await update.message.reply_text("🔑 Введите пароль:")
    return LOGIN_PASSWORD

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pwd = update.message.text.strip()
    acc = context.user_data["account"]
    if pwd != users_db[acc]["password"]:
        await update.message.reply_text("❌ Неверный пароль. Попробуйте ещё:")
        return LOGIN_PASSWORD
    await update.message.reply_text("💳 Введите PIN-код:")
    return LOGIN_PIN

async def login_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pin = update.message.text.strip()
    acc = context.user_data["account"]
    if pin != users_db[acc]["pin"]:
        await update.message.reply_text("❌ Неверный PIN. Попробуйте ещё:")
        return LOGIN_PIN
    users_db[acc]["user_id"] = update.effective_user.id
    return await show_menu(update, context)

async def show_menu(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    acc = context.user_data["account"]
    kb = [
        [InlineKeyboardButton("💎 Баланс", callback_data="balance")],
        [InlineKeyboardButton("💎 Перевести", callback_data="transfer")],
        [InlineKeyboardButton("🚪 Выйти", callback_data="logout")],
    ]
    markup = InlineKeyboardMarkup(kb)
    if update_or_query.callback_query:
        await update_or_query.callback_query.answer()
        await update_or_query.callback_query.edit_message_text(
            f"👋 {acc}, выберите действие:", reply_markup=markup
        )
    else:
        await update_or_query.message.reply_text(
            f"👋 {acc}, выберите действие:", reply_markup=markup
        )
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data
    acc = context.user_data["account"]

    if action == "balance":
        await query.answer()
        await query.edit_message_text(
            f"💎 Ваш баланс: {users_db[acc]['balance']} 💎",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Главное меню", callback_data="menu")]
            ])
        )
        return MENU

    if action == "transfer":
        await query.answer()
        await query.edit_message_text("📥 Введите счёт получателя:")
        return TRANSFER_ACCOUNT

    if action == "logout":
        context.user_data.clear()
        await query.answer()
        await query.edit_message_text("✅ Вы вышли. Введите /start для входа.")
        return ConversationHandler.END

    if action == "menu":
        return await show_menu(update, context)

async def transfer_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message.text.strip()
    if target not in users_db:
        await update.message.reply_text("❌ Счёт не найден. Попробуйте ещё:")
        return TRANSFER_ACCOUNT
    if target == context.user_data["account"]:
        await update.message.reply_text("❌ Нельзя перевести самому себе. Введите другой счёт:")
        return TRANSFER_ACCOUNT
    context.user_data["target"] = target
    await update.message.reply_text("📥 Введите сумму перевода (числом):")
    return TRANSFER_AMOUNT

async def transfer_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acc = context.user_data["account"]
    text = update.message.text.strip()
    try:
        amount = float(text)
    except:
        await update.message.reply_text("❌ Сумма должна быть числом. Попробуйте ещё:")
        return TRANSFER_AMOUNT

    if amount > 1000:
        await update.message.reply_text(
            "❌ Транзакция отменена, просим обратиться к @NoName1042"
        )
        return await show_menu(update, context)

    if amount <= 0 or users_db[acc]["balance"] < amount:
        await update.message.reply_text("❌ Недостаточно средств или некорректная сумма. Попробуйте ещё:")
        return TRANSFER_AMOUNT

    context.user_data["amount"] = amount
    # Подтверждение через инлайн-кнопки
    kb = [
        [InlineKeyboardButton("✅ Да", callback_data="yes")],
        [InlineKeyboardButton("❌ Нет", callback_data="no")],
    ]
    await update.message.reply_text(
        f"Подтвердите перевод {amount} 💎 на счёт {context.user_data['target']}:",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return TRANSFER_CONFIRM

async def transfer_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    acc = context.user_data["account"]
    target = context.user_data["target"]
    amount = context.user_data["amount"]

    if choice == "yes":
        users_db[acc]["balance"] -= amount
        users_db[target]["balance"] += amount
        await query.edit_message_text(
            f"✅ Успешно переведено {amount} 💎 на {target}.\n"
            f"💎 Ваш новый баланс: {users_db[acc]['balance']} 💎"
        )
        # Уведомление получателя
        rid = users_db[target]["user_id"]
        if rid:
            await context.bot.send_message(
                chat_id=rid,
                text=f"💸 Вы получили {amount} 💎 от {acc}. Баланс: {users_db[target]['balance']} 💎"
            )
    else:
        await query.edit_message_text("❌ Перевод отменён.")
    return await show_menu(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Операция отменена. /start")
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LOGIN_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_account)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
            LOGIN_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_pin)],
            MENU: [CallbackQueryHandler(menu_handler)],
            TRANSFER_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_account)],
            TRANSFER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_amount)],
            TRANSFER_CONFIRM: [CallbackQueryHandler(transfer_confirm, pattern="^(yes|no)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_chat=True,
    )

    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
