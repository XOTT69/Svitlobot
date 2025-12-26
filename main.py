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

HEADER_LINES = 3          # скільки верхніх рядків лишати як "шапку"
TARGET_GROUP = "Підгрупа 2.2"


def build_22_message(text: str) -> str | None:
    lines = text.splitlines()

    if TARGET_GROUP not in text:
        return None

    # шапка
    header = []
    for i, line in enumerate(lines):
        if i >= HEADER_LINES:
            break
        if line.strip():
            header.append(line)

    # шукаємо початок блоку 2.2
    start = None
    for i, line in enumerate(lines):
        if TARGET_GROUP in line:
            start = i
            break
    if start is None:
        return None

    body = []
    for line in lines[start:]:
        # закінчуємо, коли пішов наступний блок Підгрупа 3.x або порожній абзац
        if line.startswith("💡 Підгрупа") and TARGET_GROUP not in line:
            break
        body.append(line)

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
        return  # немає 2.2 – мовчимо

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
