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
TARGET = "2.2"


def build_22_message(text: str) -> str | None:
    lines = text.splitlines()

    # Шапка: усі непорожні рядки до першої пустої строки
    header = []
    for line in lines:
        if not line.strip():
            break
        header.append(line)

    # Усі рядки, де зустрічається "2.2"
    body_raw = [line for line in lines if TARGET in line]

    if not body_raw:
        return None

    # Прибираємо слова "Підгрупа", "підгрупу" і зайві двокрапки
    body = []
    for line in body_raw:
        clean = (
            line.replace("Підгрупа", "")
                .replace("підгрупу", "")
                .replace("підгрупи", "")
        )
        body.append(clean.strip())

    result = header + [""] + body
    return "\n".join(result).strip()


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
