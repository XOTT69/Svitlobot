from telegram.ext import Application, CommandHandler, ContextTypes
from tapo import ApiClient
import asyncio

# ★★★★★ ВСТАВТЕ СВОЇ ДАНІ ★★★★★
BOT_TOKEN = "8531102609:AAHzEoJR0WT1yp4tUDa7uvGWw_5V2MkrUrA"
CHAT_ID = -1003504400394
TAPO_EMAIL = mikolenko.anton1@gmail.com  # ★ ВАШ EMAIL ★
TAPO_PASS = anton979          # ★ ПАРОЛЬ Tapo app ★
# ★★★★★ КІНЕЦЬ ★★★★★

client = ApiClient(TAPO_EMAIL, TAPO_PASS)

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
    try:
        devices = await client.devices()
        for device in devices:
            if 'P110' in str(device.model):
                await device.on()
                await context.bot.send_message(CHAT_ID, f"💡 {device.nickname} УВІМКНЕНО")
                return
        await context.bot.send_message(CHAT_ID, "❌ P110 не знайдено")
    except Exception as e:
        await context.bot.send_message(CHAT_ID, f"❌ {str(e)}")

async def light_off(update, context: ContextTypes.DEFAULT_TYPE):
    try:
        devices = await client.devices()
        for device in devices:
            if 'P110' in str(device.model):
                await device.off()
                await context.bot.send_message(CHAT_ID, f"💡 {device.nickname} ВИМКНЕНО")
                return
        await context.bot.send_message(CHAT_ID, "❌ P110 не знайдено")
    except Exception as e:
        await context.bot.send_message(CHAT_ID, f"❌ {str(e)}")

async def auto_check(context: ContextTypes.DEFAULT_TYPE):
    await check_light(None, context)

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("light", check_light))
app.add_handler(CommandHandler("on", light_on))
app.add_handler(CommandHandler("off", light_off))

# Авто-чек кожні 60 секунд
app.job_queue.run_repeating(auto_check, interval=60, first=10)

print("🚀 Світлобот запущено 24/7!")
app.run_polling()

