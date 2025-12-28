import os
import time
import asyncio
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
    print(f"📱 Знайдено пристроїв: {len(devices)}")
    
    # ✅ ГНУЧКИЙ ПОШУК: PLUG, SMART.PLUG, HS300, P110
    for d in devices:
        device_type = d.get("deviceType", "").upper()
        device_name = d.get("nickname", "Unknown").upper()
        print(f"  → {device_name}: {device_type}")
        
        if any(keyword in device_type for keyword in ["PLUG", "SOCKET"]):
            device_id = d["deviceId"]
            print(f"✅ ✅ РОЗЕТКА: {device_name} ({device_type})")
            return True
    
    # Fallback: будь-який пристрій
    if devices:
        device_id = devices[0]["deviceId"]
        print(f"ℹ️ Використовуємо перший: {devices[0].get('nickname', 'Unknown')}")
        return True
    
    print("❌ Розеток НЕ ЗНАЙДЕНО")
    return False

def power_present():
    if not device_id:
        return True
    
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
        # ✅ ГНУЧКА ПЕРЕВІРКА: device_on ТІЛЬКИ для розеток
        return "device_on" in response_data and response_data.get("device_on", False)
    except Exception as e:
        print(f"⚠️ Power check error: {e}")
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
    
    if state == last_state:
        return
    
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

# ================== ASYNC MAIN ==================
async def main():
    print("🚀 === SVITLOBOT START ===")
    
    cloud_login()
    tplink_ok = fetch_device_id()
    print(f"🔌 TP-Link: {'✅ OK' if tplink_ok else '⚠️ SKIP'}")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(power_job, interval=60, first=10)
    
    print("🎉 DTEK парсер + TP-Link моніторинг АКТИВНІ!")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
