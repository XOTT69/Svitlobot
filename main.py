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
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1003534080985"))
TAPO_EMAIL = os.environ.get("TAPO_USERNAME", "mikolenko.anton1@gmail.com")
TAPO_PASSWORD = os.environ.get("TAPO_PASSWORD", "anton979")
CHECK_INTERVAL = 60

print(f"🚀 BOT_TOKEN: OK ({len(BOT_TOKEN) if BOT_TOKEN else 0}сим)")
print(f"📱 CHANNEL_ID: {CHANNEL_ID}")

CLOUD_URL = "https://eu-wap.tplinkcloud.com"
cloud_token = None
device_id = None
last_power_state = None
power_off_at = None

# ================== TP-LINK ==================
def kyiv_time():
    return datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%H:%M")

def cloud_login():
    global cloud_token
    print("🔌 TP-Link логін...")
    try:
        r = requests.post(f"{CLOUD_URL}/", json={
            "method": "login", "params": {
                "appType": "Tapo_Android",
                "cloudUserName": TAPO_EMAIL,
                "cloudPassword": TAPO_PASSWORD,
                "terminalUUID": "svitlobot"
            }
        }, timeout=15).json()
        cloud_token = r["result"]["token"]
        print("✅ TP-Link OK")
        return True
    except Exception as e:
        print(f"⚠️ TP-Link skip: {e}")
        return False

def fetch_device_id():
    global device_id
    print("🔍 Tapo пристрої...")
    try:
        r = requests.post(f"{CLOUD_URL}/?token={cloud_token}", json={"method": "getDeviceList"}, timeout=15).json()
        devices = r["result"]["deviceList"]
        for d in devices:
            if "PLUG" in (d.get("deviceType") or "").upper():
                device_id = d["deviceId"]
                print(f"✅ РОЗЕТКА: {device_id[:8]}")
                return True
        if devices:
            device_id = devices[0]["deviceId"]
            print(f"ℹ️ Device: {device_id[:8]}")
            return True
        return False
    except:
        return False

def power_present():
    if not device_id: return True
    try:
        r = requests.post(f"{CLOUD_URL}/?token={cloud_token}", json={
            "method": "passthrough", "params": {
                "deviceId": device_id, "requestData": '{"method":"get_device_info"}'
            }
        }, timeout=10).json()
        return bool(r["result"]["responseData"])
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
    global last_power_state, power_off_at
    state = power_present()
    if state != last_power_state:
        now = kyiv_time()
        if not state:
            power_off_at = time.time()
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"⚡ Світло зникло — {now}")
        else:
            minutes = int((time.time() - power_off_at) / 60) if power_off_at else 0
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"🔌 Світло зʼявилось — {now}\n⏱️ Не було: {minutes} хв")
        last_power_state = state

# ================== MAIN ==================
def main():
    print("🚀 === SVITLOBOT READY ===")
    
    # TP-Link
    cloud_ok = cloud_login()
    if cloud_ok:
        fetch_device_id()
    
    print("🤖 Telegram Application...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # ✅ JobQueue вбудований у v20.8
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(power_job, interval=CHECK_INTERVAL, first=5)
    
    print("🎉 ✅ БОТ + МОНІТОРИНГ 100% АКТИВНІ!")
    app.run_polling()

if __name__ == "__main__":
    main()
