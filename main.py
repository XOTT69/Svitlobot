import os
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# CONFIG
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1003534080985"))
TAPO_EMAIL = os.environ["TAPO_USERNAME"]
TAPO_PASSWORD = os.environ["TAPO_PASSWORD"]
CLOUD_URL = "https://eu-wap.tplinkcloud.com"

cloud_token = None
device_id = None
last_state = None
power_off_at = None

def kyiv_time():
    return datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%H:%M")

def cloud_login():
    global cloud_token
    print("🔌 TP-Link логін...")
    r = requests.post(CLOUD_URL, json={
        "method": "login", "params": {
            "appType": "Tapo_Android",
            "cloudUserName": TAPO_EMAIL,
            "cloudPassword": TAPO_PASSWORD,
            "terminalUUID": "svitlobot"
        }
    }, timeout=15).json()
    cloud_token = r["result"]["token"]
    print("✅ Логін OK")

def fetch_device_id():
    global device_id
    print("🔍 Розетки...")
    r = requests.post(f"{CLOUD_URL}/?token={cloud_token}", json={"method": "getDeviceList"}, timeout=15).json()
    devices = r["result"]["deviceList"]
    
    for d in devices:
        if "PLUG" in d.get("deviceType", "").upper():
            device_id = d["deviceId"]
            print(f"✅ P110: {d.get('nickname', 'Unknown')} ID={device_id[:8]}")
            return True
    
    print("⚠️ P110 НЕ ЗНАЙДЕНО")
    return False

def power_present():
    """✅ P110: онлайн = світло Є, офлайн = світла НЕМАЄ"""
    if not device_id: return True
    
    try:
        r = requests.post(
            f"{CLOUD_URL}/?token={cloud_token}",
            json={
                "method": "passthrough",
                "params": {
                    "deviceId": device_id,
                    "requestData": '{"method":"get_device_info"}'
                }
            },
            timeout=10
        ).json()
        
        # ✅ P110 ЛОГІКА: якщо responseData Є = розетка онлайн = СВІТЛО Є
        has_response = bool(r["result"].get("responseData"))
        device_on = r["result"]["responseData"].get("device_on", False) if has_response else False
        
        print(f"🔌 P110: response={has_response}, device_on={device_on}")
        return has_response  # ✅ КЛЮЧ: онлайн = світло!
        
    except Exception as e:
        print(f"⚠️ P110 помилка: {e}")
        return False  # ❌ Offline = немає світла

def build_22_message(text: str):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines: return None
    header = lines[0]
    for line in lines:
        if "2.2" in line and ("Підгрупа" in line or "підгрупу" in line):
            return f"{header}\n\n📍 {line}"
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or update.message.caption or ""
    payload = build_22_message(text)
    if payload:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=payload)

async def power_job(context: ContextTypes.DEFAULT_TYPE):
    global last_state, power_off_at
    state = power_present()
    
    print(f"⏰ [{kyiv_time()}] Світло: {'Є' if state else 'НЕМАЄ'}")
    
    if state == last_state: 
        return
    
    now = kyiv_time()
    if not state:
        power_off_at = time.time()
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"⚡ Світло зникло — {now}")
        print(f"🚨 АВАРІЯ: {now}")
    else:
        minutes = int((time.time() - power_off_at) / 60) if power_off_at else 0
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"🔌 Світло зʼявилось — {now}\n⏱️ Не було: {minutes} хв")
        print(f"✅ ВІДНОВЛЕНО: {now}")
    
    last_state = state

def main():
    print("🚀 SVITLOBOT P110")
    cloud_login()
    if fetch_device_id():
        print("✅ Розетка готова!")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(power_job, interval=30, first=10)  # ⏱️ 30 сек
    
    print("🎉 DTEK 2.2 + P110 МОНІТОРИНГ!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
