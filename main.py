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
    lines = text.splitlines()

    # знайти перший непорожній рядок як шапку
    header = None
    header_index = None
    for i, line in enumerate(lines):
        if line.strip():
            header = line
            header_index = i
            break
    if header is None:
        return None

    # знайти перший рядок, де є "2.2"
    start = None
    for i, line in enumerate(lines):
        if "2.2" in line:
            start = i
            break

    if start is None:
        # немає 2.2 → можна, наприклад, нічого не слати
        # або повернути тільки шапку, якщо це зміни в графіку
        if "Зміни у графіку" in header:
            return header
        return None

    # збираємо блок 2.2 до першої пустої строки після нього
    block = []
    for line in lines[start:]:
        if line.strip() == "" and block:
            break
        block.append(line)

    # чистимо порожні рядки на краях
    block = [l for l in block if l.strip()]

    result_lines = [header, ""] + block
    return "\n".join(result_lines).strip()


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
