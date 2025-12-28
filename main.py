import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from tapo import ApiClient

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID'))
client = ApiClient(os.getenv('TAPO_EMAIL'), os.getenv('TAPO_PASS'))

async def check_light(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Знаходимо всі пристрої в хмарі
        devices = await client.devices()
        for device in devices:
            if 'P110' in device.model or 'plug' in device.model.lower():
                state = await device.state()
                status = "✅ Світло Є" if state.state else "❌ Світла нема"
                energy = f"{state.energy_usage:.1f} Вт" if state.energy_usage else "N/A"
                msg = f"{status} | {energy} | {device.nickname}"
                await context.bot.send_message(CHAT_ID, msg)
                return
        await context.bot.send_message(CHAT_ID, "❌ P110 не знайдено в хмарі")
    except Exception as e:
        await context.bot.send_message(CHAT_ID, f"❌ Помилка: {str(e)}")

async def light_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    devices = await client.devices()
    for device in devices:
        if 'P110' in device.model:
            await device.on()
            await context.bot.send_message(CHAT_ID, f"💡 {device.nickname} УВІМКНЕНО")
            return
    await context.bot.send_message(CHAT_ID, "❌ P110 не знайдено")

async def light_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    devices = await client.devices()
    for device in devices:
        if 'P110' in device.model:
            await device.off()
            await context.bot.send_message(CHAT_ID, f"💡 {device.nickname} ВИМКНЕНО")
            return
    await context.bot.send_message(CHAT_ID, "❌ P110 не знайдено")

async def auto_check(context: ContextTypes.DEFAULT_TYPE):
    await check_light(None, context)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("light", check_light))
    app.add_handler(CommandHandler("on", light_on))
    app.add_handler(CommandHandler("off", light_off))
    
    # Авто-чек кожні 60с
    app.job_queue.run_repeating(auto_check, interval=60, first=10)
    
    print("🚀 Світлобот запущено!")
    app.run_polling()

if __name__ == '__main__':
    main()
