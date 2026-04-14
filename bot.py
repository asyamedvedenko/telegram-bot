import logging
import os
import json

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- ENV SAFETY ----------------
TOKEN = os.environ.get("BOT_TOKEN")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in environment variables")

if not GOOGLE_CREDENTIALS:
    raise RuntimeError("GOOGLE_CREDENTIALS is missing in environment variables")

# ---------------- GOOGLE SHEETS ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(GOOGLE_CREDENTIALS)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)
sheet = client.open("Consultations_Bot").sheet1

# ---------------- MENUS ----------------
main_menu = [["Апрель", "Май"]]

april_dates = [
    ["14.04 онлайн", "17.04 офлайн"],
    ["21.04 онлайн", "24.04 офлайн"],
    ["28.04 онлайн"]
]

may_dates = [
    ["05.05 онлайн", "08.05 офлайн"],
    ["12.05 онлайн", "15.05 офлайн"],
    ["19.05 онлайн", "22.05 офлайн"],
    ["26.05 онлайн", "29.05 офлайн"]
]

potok_menu = [
    ["B1.1/25", "B2/27"],
    ["B2/44", "B2/47"],
    ["B2/55", "B2/57"],
    ["C1/6", "C1/9"]
]

after_booking_menu = [
    ["Мне нужна еще одна запись"],
    ["Больше записей не требуется"]
]

back_menu = [["Я передумал(а), мне нужна еще запись"]]

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["step"] = "name"

    await update.message.reply_text("Введите вашу фамилию и имя:")

# ---------------- MAIN HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    data = context.user_data

    logger.info(f"STEP: {data.get('step')} | TEXT: {text}")

    if "step" not in data:
        data["step"] = "name"
        await update.message.reply_text("Введите вашу фамилию и имя:")
        return

    # -------- NAME --------
    if data["step"] == "name":
        data["name"] = text
        data["step"] = "potok"

        await update.message.reply_text(
            "Выберите ваш поток:",
            reply_markup=ReplyKeyboardMarkup(potok_menu, resize_keyboard=True)
        )
        return

    # -------- POTOK --------
    if data["step"] == "potok":
        all_potoks = sum(potok_menu, [])

        if text not in all_potoks:
            await update.message.reply_text("Пожалуйста, выберите поток с помощью кнопок.")
            return

        data["potok"] = text
        data["step"] = "menu"

        await update.message.reply_text(
            "Выберите месяц:",
            reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
        )
        return

    # -------- MENU --------
    if data["step"] == "menu":

        if text == "Апрель":
            data["step"] = "date"
            await update.message.reply_text(
                "Выберите дату:",
                reply_markup=ReplyKeyboardMarkup(april_dates, resize_keyboard=True)
            )
            return

        if text == "Май":
            data["step"] = "date"
            await update.message.reply_text(
                "Выберите дату. Онлайн — только speaking. Офлайн — все части (writing, test).",
                reply_markup=ReplyKeyboardMarkup(may_dates, resize_keyboard=True)
            )
            return

        return

    # -------- DATE --------
    if data["step"] == "date":
        all_dates = sum(april_dates + may_dates, [])

        if text not in all_dates:
            return

        sheet.append_row([
            update.message.from_user.id,
            data["name"],
            data["potok"],
            text,
            "booked"
        ])

        data["step"] = "after_booking"

        await update.message.reply_text(
            f"Вы записаны на {text}",
            reply_markup=ReplyKeyboardMarkup(after_booking_menu, resize_keyboard=True)
        )
        return

    # -------- AFTER BOOKING --------
    if data["step"] == "after_booking":

        if text == "Мне нужна еще одна запись":
            data["step"] = "menu"
            await update.message.reply_text(
                "Выберите месяц:",
                reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
            )
            return

        if text == "Больше записей не требуется":
            data["step"] = "done"
            await update.message.reply_text(
                "Отлично! Увидимся на консультации.",
                reply_markup=ReplyKeyboardMarkup(back_menu, resize_keyboard=True)
            )
            return

        return

    # -------- DONE --------
    if data["step"] == "done":

        if text == "Я передумал(а), мне нужна еще запись":
            data["step"] = "menu"
            await update.message.reply_text(
                "Выберите месяц:",
                reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
            )
            return

        return

# ---------------- RUN BOT ----------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
