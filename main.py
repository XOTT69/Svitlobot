import os
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from tapo import ApiClient

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID'))
client = ApiClient(os.getenv('TAPO_EMAIL'), os.getenv('TAPO_PASS'))

async def check_light(update, context: ContextTypes.DEFAULT_TYPE):
    try:
        devices = await client.devices()
        for device in devices:
            if 'P110' in str(device.model):
                state = await device.state()
                status = "✅ Світло Є" if state.state else "❌ Світла нема"
                await context.bot.send_message(CHAT_ID, f"{status} | {device.nickname}")
                return
        await context.bot.send_message(CHAT_ID, "❌ P110 не знайдено")
    except Exception as e:
        await context.bot.send_message(CHAT_ID, f"❌ {str(e)}")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("light", check_light))
print("🚀 Бот запущено!")
app.run_polling()
