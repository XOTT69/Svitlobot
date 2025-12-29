import os
import asyncio
from telegram.ext import Application, CommandHandler, ContextTypes
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

async def light_on(update, context: ContextTypes.DEFAULT_TYPE):
    devices = await client.devices()
    for device in devices:
        if 'P110' in str(device.model):
            await device.on()
            await context.bot.send_message(CHAT_ID, f"💡 {device.nickname} УВІМКНЕНО")
            return
    await context.bot.send_message(CHAT_ID, "❌ P110 не знайдено")

async def light_off(update, context: ContextTypes.DEFAULT_TYPE):
    devices = await client.devices()
    for device in devices:
        if 'P110' in str(device.model):
            await device.off()
            await context.bot.send_message(CHAT_ID, f"💡 {device.nickname} ВИМКНЕНО")
            return
    await context.bot.send_message(CHAT_ID, "❌ P110 не знайдено")

async def auto_check(context: ContextTypes.DEFAULT_TYPE):
    await check_light(None, context)

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("light", check_light))
app.add_handler(CommandHandler("on", light_on))
app.add_handler(CommandHandler("off", light_off))

# Авто-чек кожні 60с
app.job_queue.run_repeating(auto_check, interval=60, first=10)

print("🚀 Світлобот запущено 24/7!")
app.run_polling()
