import requests
import json
from telegram.ext import Application, CommandHandler, ContextTypes

# ВАШІ ДАНІ
BOT_TOKEN = "8531102609:AAHzEoJR0WT1yp4tUDa7uvGWw_5V2MkrUrA"
CHAT_ID = -1003504400394
TAPO_EMAIL = "mikolenko.anton1@gmail.com"
TAPO_PASS = "anton979"

async def check_light(update, context):
    try:
        # 1. Логін в TP-Link хмару
        login_data = {
            "method": "login",
            "params": {
                "username": TAPO_EMAIL,
                "password": TAPO_PASS
            }
        }
        login = requests.post("https://wap.tplinkcloud.com/tapo/auth", json=login_data, timeout=10).json()
        token = login['result']['token']
        
        # 2. Отримуємо список пристроїв
        headers = {'Authorization': f'bearer {token}'}
        devices = requests.post("https://wap.tplinkcloud.com/tapo/cloudaccess/device_list", 
                               json={"method": "getDeviceList"}, 
                               headers=headers, timeout=10).json()
        
        # 3. Шукаємо P110
        for device in devices['result']['deviceList']:
            if 'P110' in device['deviceModel']:
                status = "✅ Світло Є" if device['device_state']['state'] else "❌ Світла нема"
                await context.bot.send_message(CHAT_ID, f"{status} | {device['alias']}")
                return
        
        await context.bot.send_message(CHAT_ID, "❌ P110 не знайдено")
        
    except Exception as e:
        await context.bot.send_message(CHAT_ID, f"❌ Помилка: {str(e)}")

async def light_on(update, context):
    await context.bot.send_message(CHAT_ID, "💡 /on — Симуляція (API обмежений)")

async def light_off(update, context):
    await context.bot.send_message(CHAT_ID, "💡 /off — Симуляція (API обмежений)")

async def test(update, context):
    await context.bot.send_message(CHAT_ID, "🟢 Світлобот РОБОТАЄ 24/7!")

# Запуск
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("test", test))
app.add_handler(CommandHandler("light", check_light))
app.add_handler(CommandHandler("on", light_on))
app.add_handler(CommandHandler("off", light_off))

print("🚀 Світлобот запущено!")
app.run_polling()
