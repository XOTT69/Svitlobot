import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = -1003534080985


def build_22_message(text: str) -> str | None:
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return None

    header = lines[0]

    line_22 = None
    for line in lines:
        if "2.2" in line:
            line_22 = line
            break

    if not line_22:
        if "Зміни у графіку" in header:
            return header
        return None

    if line_22 == header:
        return line_22

    return f"{header}\n{line_22}"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    text = msg.text or msg.caption or ""
    if not text:
        return

    payload = build_22_message(text)
    if not payload:
        return

    await context.bot.send_message(chat_id=CHANNEL_ID, text=payload)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(
        (filters.TEXT | filters.CAPTION) & ~filters.COMMAND,
        handle_message,
    ))

    app.run_polling()


if __name__ == "__main__":
    main()
