import requests
import json
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8531102609:AAHzEoJR0WT1yp4tUDa7uvGWw_5V2MkrUrA"
CHAT_ID = -1003504400394
TAPO_EMAIL = "mikolenko.anton1@gmail.com"
TAPO_PASS = "anton979"

async def check_light(update, context):
    try:
        # Хмарний логін TP-Link
        login = requests.post("https://wap.tplinkcloud.com/tapo/auth", json={
            "method": "login",
            "params": {
                "username": TAPO_EMAIL,
                "password": TAPO_PASS
            }
        }).json()
        
        token = login['result']['token']
        
        # Отримуємо пристрої
        devices = requests.post("https://wap.tplinkcloud.com/tapo/cloudaccess/device_list", json={
            "method": "getDeviceList",
            "params": {}
        }, headers={'Authorization': f'bearer {token}'}).json()
        
        for device in devices['result']['deviceList']:
            if 'P110' in device['deviceModel']:
                status = "✅ Світло Є" if device['online'] and device['state'] else "❌ Світла нема"
                await context.bot.send_message(CHAT_ID, f"{status} | {device['alias']}")
                return
        
        await context.bot.send_message(CHAT_ID, "❌ P110 не знайдено")
    except Exception as e:
        await context.bot.send_message(CHAT_ID, f"❌ {str(e)}")

async def test(update, context):
    await context.bot.send_message(CHAT_ID, "🟢 Світлобот РОБОТАЄ!")

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("light", check_light))
app.add_handler(CommandHandler("test", test))
print("🚀 Запущено!")
app.run_polling()

