import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]  # only variable needed in Railway

# Change this to your real brand name
BRAND = "YourBrand"

WELCOME = (
    f"Welcome to {BRAND} Rewards!\n\n"
    "Here you can:\n"
    "- Check your points balance\n"
    "- See how to earn more points\n\n"
    "Choose an option below."
)


def menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("My points", callback_data="points")],
        [InlineKeyboardButton("How to earn", callback_data="earn")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, reply_markup=menu())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - main menu\n/help - this message")


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "points":
        # TODO: replace with a real lookup from your database
        await q.edit_message_text("Your balance: 0 points", reply_markup=menu())
    elif q.data == "earn":
        # TODO: describe your real earning rules
        await q.edit_message_text(
            "Earn points with every purchase. Replace this with your real rules.",
            reply_markup=menu(),
        )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling()


if __name__ == "__main__":
    main()
