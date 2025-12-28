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

# ================== CONFIG ==================
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1003534080985"))
TAPO_EMAIL = os.environ["TAPO_USERNAME"]
TAPO_PASSWORD = os.environ["TAPO_PASSWORD"]
CLOUD_URL = "https://eu-wap.tplinkcloud.com"

cloud_token = None
device_id = None
last_state = None
power_off_at = None

# ================== HELPERS ==================
def kyiv_time():
    return datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%H:%M")

# ================== TP-LINK CLOUD ==================
def cloud_login():
    global cloud_token
    print("🔌 Логін TP-Link...")
    r = requests.post(CLOUD_URL, json={
        "method": "login",
        "params": {
            "appType": "Tapo_Android",
            "cloudUserName": TAPO_EMAIL,
            "cloudPassword": TAPO_PASSWORD,
            "terminalUUID": "svitlobot"
        }
    }, timeout=15).json()
    cloud_token = r["result"]["token"]
    print("✅ Авторизація OK")

def fetch_device_id():
    global device_id
    print("🔍 Шукаємо розетку...")
    r = requests.post(
        f"{CLOUD_URL}/?token={cloud_token}",
        json={"method": "getDeviceList"},
        timeout=15
    ).json()

    devices = r["result"]["deviceList"]
    print(f"📱 Пристроїв: {len(devices)}")
    
    for d in devices:
        device_type = d.get("deviceType", "").upper()
        device_name = d.get("nickname", "Unknown")
        print(f"  → {device_name}: {device_type}")
        
        if "PLUG" in device_type:
            device_id = d["deviceId"]
            print(f"✅ РОЗЕТКА: {device_name} ({device_type})")
            return True
    
    if devices:
        device_id = devices[0]["deviceId"]
        print(f"ℹ️ Fallback: {devices[0].get('nickname', 'Unknown')}")
        return True
    
    print("⚠️ Розеток НЕТ")
    return False

def power_present():
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
        
        response_data = r["result"]["responseData"]
        return response_data.get("device_on", True) if "device_on" in response_data else True
    except:
        return True

# ================== DTEK 2.2 ==================
def build_22_message(text: str):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines: return None
    header = lines[0]
    for line in lines:
        if "2.2" in line and ("Підгрупа" in line or "підгрупу" in line):
            return f"{header}\n\n📍 {line}"
    return None

# ================== HANDLERS ==================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or update.message.caption or ""
    payload = build_22_message(text)
    if payload:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=payload)

async def power_job(context: ContextTypes.DEFAULT_TYPE):
    global last_state, power_off_at
    state = power_present()
    
    if state == last_state: return
    
    now = kyiv_time()
    if not state:
        power_off_at = time.time()
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"⚡ Світло зникло — {now}")
        print(f"⚡ БЕЗ СВІТЛА: {now}")
    else:
        minutes = int((time.time() - power_off_at) / 60) if power_off_at else 0
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"🔌 Світло зʼявилось — {now}\n⏱️ Не було: {minutes} хв")
        print(f"🔌 СВІТЛО Є: {now}")
    
    last_state = state

# ================== RAILWAY COMPATIBLE MAIN ==================
def main():
    print("🚀 === SVITLOBOT START ===")
    
    cloud_login()
    tplink_ok = fetch_device_id()
    print(f"🔌 TP-Link: {'✅ OK' if tplink_ok else '⚠️ NO'}")
    
    print("🤖 Telegram bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    print(f"✅ JobQueue: {'OK' if app.job_queue else 'FAIL'}")
    
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(power_job, interval=60, first=10)
    
    print("🎉 ✅ ✅ DTEK + TP-Link АКТИВНІ!")
    print("🚀 Railway-сумісний polling...")
    
    # ✅ RAILWAY FIX: синхронний run_polling
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
