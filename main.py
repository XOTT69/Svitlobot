iimport os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from tapo import ApiClient

BOT_TOKEN = "8531102609:AAHzEoJR0WT1yp4tUDa7uvGWw_5V2MkrUrA"
CHAT_ID = -1003504400394
TAPO_EMAIL = "mikolenko.anton1@gmail.com"
TAPO_PASS = "anton979"

client = ApiClient(TAPO_EMAIL, TAPO_PASS)

async def check_light(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        device = await client.p110("192.168.50.253")  # ВАШ IP!
        state = await device.state()
        status = "✅ Світло Є" if state.state else "❌ Світла нема"
        await context.bot.send_message(CHAT_ID, f"{status}")
    except Exception as e:
        await context.bot.send_message(CHAT_ID, f"❌ {str(e)}")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(CHAT_ID, "🟢 Бот працює!")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("light", check_light))
app.add_handler(CommandHandler("test", test))
app.run_polling()
