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
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
TAPO_EMAIL = os.environ["TAPO_USERNAME"]
TAPO_PASSWORD = os.environ["TAPO_PASSWORD"]
TAPO_REGION = "eu"
CHECK_INTERVAL = 60

# Глобальні змінні
CLOUD_URL = f"https://{TAPO_REGION}-wap.tplinkcloud.com"
cloud_token = None
device_id = None
last_power_state = None
power_off_at = None

# ================== UTIL ==================
def kyiv_time():
    return datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%H:%M")

# ================== TP-LINK ==================
def cloud_login():
    global cloud_token
    r = requests.post(f"{CLOUD_URL}/", json={
        "method": "login", "params": {
            "appType": "Tapo_Android",
            "cloudUserName": TAPO_EMAIL,
            "cloudPassword": TAPO_PASSWORD,
            "terminalUUID": "svitlobot"
        }
    }, timeout=15).json()
    cloud_token = r["result"]["token"]

def fetch_device_id():
    global device_id
    r = requests.post(f"{CLOUD_URL}/?token={cloud_token}", json={"method": "getDeviceList"}, timeout=15).json()
    devices = r["result"]["deviceList"]
    for d in devices:
        if "PLUG" in (d.get("deviceType") or "").upper():
            device_id = d["deviceId"]
            return
    if devices: 
        device_id = devices[0]["deviceId"]
    else: 
        raise RuntimeError("Tapo не знайдено")

def power_present():
    try:
        r = requests.post(f"{CLOUD_URL}/?token={cloud_token}", json={
            "method": "passthrough", "params": {
                "deviceId": device_id,
                "requestData": '{"method":"get_device_info"}'
            }
        }, timeout=15).json()
        return bool(r["result"]["responseData"])
    except: 
        return False

# ================== DTEK PARSER ==================
def build_22_message(text: str):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines: return None
    header = lines[0]
    for line in lines:
        if "2.2" in line and ("Підгрупа" in line or "підгрупу" in line):
            return f"{header}\n\n{line}"
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
    print("🚀 Ініціалізація TP-Link...")
    cloud_login()
    fetch_device_id()
    print(f"✅ Tapo: {device_id[:8]}...")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, handle_message))
    
    app.job_queue.run_repeating(power_job, interval=CHECK_INTERVAL, first=5)
    
    print(f"🚀 Бот запущено! Перевірка кожні {CHECK_INTERVAL}с")
    app.run_polling()

if __name__ == "__main__":
    main()
