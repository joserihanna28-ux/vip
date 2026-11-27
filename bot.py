import ast
import io
import logging
import math
import operator
import os
import re

import qrcode
from deep_translator import GoogleTranslator
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================
# CONFIGURATION
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================
# MAIN MENU
# =========================

MAIN_MENU = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📝 Text Formatter", callback_data="formatter"),
        InlineKeyboardButton("🔢 Word Counter", callback_data="counter"),
    ],
    [
        InlineKeyboardButton("🌐 Text Translator", callback_data="translator"),
        InlineKeyboardButton("🔳 QR Generator", callback_data="qr"),
    ],
    [
        InlineKeyboardButton("🧮 Calculator", callback_data="calculator"),
    ],
    [
        InlineKeyboardButton("ℹ️ Help", callback_data="help"),
    ],
])

FORMAT_MENU = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("UPPERCASE", callback_data="fmt_upper"),
        InlineKeyboardButton("lowercase", callback_data="fmt_lower"),
    ],
    [
        InlineKeyboardButton("Title Case", callback_data="fmt_title"),
        InlineKeyboardButton("Clean Text", callback_data="fmt_clean"),
    ],
    [
        InlineKeyboardButton("↩️ Main Menu", callback_data="home"),
    ],
])


# =========================
# SAFE CALCULATOR
# =========================

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def safe_calculate(expression):

    if len(expression) > 100:
        raise ValueError("Calculation is too long.")

    tree = ast.parse(expression, mode="eval")

    def calculate(node):

        if isinstance(node, ast.Expression):
            return calculate(node.body)

        if isinstance(node, ast.Constant):
            if type(node.value) in (int, float):
                return node.value

        if isinstance(node, ast.BinOp):
            if type(node.op) not in OPERATORS:
                raise ValueError("Unsupported mathematical operator.")

            left = calculate(node.left)
            right = calculate(node.right)

            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Power is too large.")

            result = OPERATORS[type(node.op)](left, right)

            if not math.isfinite(float(result)) or abs(result) > 10**100:
                raise ValueError("Result is too large.")

            return result

        if isinstance(node, ast.UnaryOp):
            if type(node.op) not in OPERATORS:
                raise ValueError("Unsupported operator.")

            return OPERATORS[type(node.op)](
                calculate(node.operand)
            )

        raise ValueError(
            "Use numbers and basic operators: + - * / // % **"
        )

    return calculate(tree)


# =========================
# START COMMAND
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    await update.message.reply_text(
        "Welcome to Smart Tools Bot! 👋\n\n"
        "Your simple collection of everyday digital tools.\n\n"
        "Choose what you want to do:\n\n"
        "📝 Format your text\n"
        "🔢 Count words and characters\n"
        "🌐 Translate text\n"
        "🔳 Generate QR codes\n"
        "🧮 Calculate numbers\n\n"
        "Select a tool below to begin.",
        reply_markup=MAIN_MENU,
    )


# =========================
# HELP COMMAND
# =========================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "SMART TOOLS BOT - HELP\n\n"
        "📝 Text Formatter: Change text case and clean spaces.\n\n"
        "🔢 Word Counter: Count words, characters and lines.\n\n"
        "🌐 Translator: Translate text into another language.\n\n"
        "🔳 QR Generator: Create QR codes from text or links.\n\n"
        "🧮 Calculator: Solve basic mathematical calculations.\n\n"
        "Use /start to open the main menu.\n"
        "Use /cancel to cancel your current task.",
        reply_markup=MAIN_MENU,
    )


# =========================
# CANCEL COMMAND
# =========================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    await update.message.reply_text(
        "Your current task has been cancelled.\n\n"
        "Choose another tool below.",
        reply_markup=MAIN_MENU,
    )


# =========================
# BUTTON HANDLER
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    choice = query.data

    # Return to home
    if choice == "home":

        context.user_data.clear()

        await query.message.reply_text(
            "Welcome back! Choose a tool:",
            reply_markup=MAIN_MENU,
        )
        return

    # Help
    if choice == "help":

        await query.message.reply_text(
            "Choose a tool from the menu and follow the instructions.",
            reply_markup=MAIN_MENU,
        )
        return

    # Text formatting
    if choice.startswith("fmt_"):

        original = context.user_data.get("formatter_text")

        if not original:
            await query.message.reply_text(
                "Please select Text Formatter and send your text first.",
                reply_markup=MAIN_MENU,
            )
            return

        action = choice.replace("fmt_", "", 1)

        if action == "upper":
            result = original.upper()

        elif action == "lower":
            result = original.lower()

        elif action == "title":
            result = original.title()

        elif action == "clean":
            result = "\n".join(
                re.sub(r"[ \t]+", " ", line.strip())
                for line in original.splitlines()
                if line.strip()
            )

        else:
            return

        context.user_data.pop("formatter_text", None)

        await query.message.reply_text(
            "Formatted text:\n\n" + result,
            reply_markup=MAIN_MENU,
        )
        return

    # Tool selection
    prompts = {

        "formatter": (
            "formatter",
            "Send the text you want to format."
        ),

        "counter": (
            "counter",
            "Send the text you want to count."
        ),

        "translator": (
            "translator",
            "Enter the target language, followed by | and your text.\n\n"
            "Example:\nSpanish | Good morning"
        ),

        "qr": (
            "qr",
            "Send the text or website link for your QR code."
        ),

        "calculator": (
            "calculator",
            "Enter your calculation.\n\n"
            "Example: (25 + 5) * 2"
        ),
    }

    if choice not in prompts:
        return

    mode, message = prompts[choice]

    context.user_data.clear()
    context.user_data["mode"] = mode

    await query.message.reply_text(
        message,
        reply_markup=MAIN_MENU,
    )


# =========================
# TEXT HANDLER
# =========================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_text = (update.message.text or "").strip()

    mode = context.user_data.get("mode")

    if not mode:

        await update.message.reply_text(
            "Please choose a tool from the menu or type /start.",
            reply_markup=MAIN_MENU,
        )
        return

    # -------------------------
    # TEXT FORMATTER
    # -------------------------

    if mode == "formatter":

        if not user_text:
            await update.message.reply_text("Please send some text.")
            return

        context.user_data["formatter_text"] = user_text

        await update.message.reply_text(
            "Choose your preferred text format:",
            reply_markup=FORMAT_MENU,
        )
        return

    # Other tools process one input at a time.
    context.user_data.pop("mode", None)

    try:

        # -------------------------
        # WORD COUNTER
        # -------------------------

        if mode == "counter":

            words = re.findall(
                r"\b[\w'-]+\b",
                user_text,
                flags=re.UNICODE,
            )

            characters = len(user_text)

            characters_without_spaces = len(
                re.sub(r"\s", "", user_text)
            )

            lines = len(user_text.splitlines())

            await update.message.reply_text(
                "📊 TEXT STATISTICS\n\n"
                f"Words: {len(words)}\n"
                f"Characters: {characters}\n"
                f"Characters without spaces: {characters_without_spaces}\n"
                f"Lines: {lines}",
                reply_markup=MAIN_MENU,
            )

        # -------------------------
        # TRANSLATOR
        # -------------------------

        elif mode == "translator":

            if "|" not in user_text:
                raise ValueError(
                    "Use this format:\n\n"
                    "Target language | Your text\n\n"
                    "Example:\nFrench | How are you?"
                )

            language, text_to_translate = user_text.split("|", 1)

            language = language.strip()
            text_to_translate = text_to_translate.strip()

            if not language or not text_to_translate:
                raise ValueError(
                    "Please provide both a language and text."
                )

            translated = GoogleTranslator(
                source="auto",
                target=language,
            ).translate(text_to_translate)

            await update.message.reply_text(
                f"🌐 TRANSLATION ({language})\n\n{translated}",
                reply_markup=MAIN_MENU,
            )

        # -------------------------
        # QR CODE GENERATOR
        # -------------------------

        elif mode == "qr":

            if not user_text:
                raise ValueError("Please enter text or a website link.")

            if len(user_text) > 1500:
                raise ValueError("Please keep the content below 1,500 characters.")

            qr = qrcode.QRCode(
                box_size=8,
                border=3,
            )

            qr.add_data(user_text)
            qr.make(fit=True)

            image = qr.make_image(
                fill_color="black",
                back_color="white",
            )

            output = io.BytesIO()
            output.name = "smart-tools-qr.png"

            image.save(output, format="PNG")
            output.seek(0)

            await update.message.reply_photo(
                photo=output,
                caption="Your QR code is ready! ✅",
                reply_markup=MAIN_MENU,
            )

        # -------------------------
        # CALCULATOR
        # -------------------------

        elif mode == "calculator":

            result = safe_calculate(user_text)

            await update.message.reply_text(
                f"🧮 CALCULATOR RESULT\n\n{result}",
                reply_markup=MAIN_MENU,
            )

    except ZeroDivisionError:

        await update.message.reply_text(
            "You cannot divide by zero.",
            reply_markup=MAIN_MENU,
        )

    except Exception as error:

        logger.warning("Tool processing error: %s", error)

        await update.message.reply_text(
            "Sorry, I couldn't process that request.\n\n"
            f"Details: {error}",
            reply_markup=MAIN_MENU,
        )


# =========================
# APPLICATION STARTUP
# =========================

def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing. Add your new token in Railway Variables."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler,
        )
    )

    logger.info("Smart Tools Bot is starting...")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
