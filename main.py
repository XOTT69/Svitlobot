import os
from telegram.ext import Application, CommandHandler, ContextTypes
from tapo import ApiClient

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID') or '-1003504400394')
client = ApiClient(os.getenv('TAPO_EMAIL'), os.getenv('TAPO_PASS'))

async def check_light(update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(CHAT_ID, "🧪 ТЕСТ: Бот працює!")
        # Тут Tapo код після тестування
    except Exception as e:
        await context.bot.send_message(CHAT_ID, f"❌ {str(e)}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("light", check_light))
    print("🚀 Світлобот запущено!")
    app.run_polling()

if __name__ == '__main__':
    main()
