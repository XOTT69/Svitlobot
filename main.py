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

def fetch_device_id():
    global device_id
    r = requests.post(
        f"{CLOUD_URL}/?token={cloud_token}",
        json={"method": "getDeviceList"},
        timeout=15
    ).json()

    for d in r["result"]["deviceList"]:
        if d.get("deviceType", "").upper() == "SMART.PLUG":
            device_id = d["deviceId"]
            return

    raise RuntimeError("❌ Tapo P110 не знайдено")

def power_present():
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

    return "device_on" in r["result"]["responseData"]

# ================== DTEK 2.2 FILTER ==================
def build_22_message(text: str):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return None

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
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"⚡ Світло зникло — {now}"
        )
    else:
        minutes = int((time.time() - power_off_at) / 60) if power_off_at else 0
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"🔌 Світло зʼявилось — {now}\n⏱️ Не було: {minutes} хв"
        )

    last_state = state

# ================== MAIN ==================
def main():
    print("🚀 SVITLOBOT START")

    cloud_login()
    fetch_device_id()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.CAPTION) & ~filters.COMMAND,
            handle_message
        )
    )

    app.job_queue.run_repeating(power_job, interval=60, first=10)

    print("✅ Bot + JobQueue running")
    app.run_polling()

if __name__ == "__main__":
    main()
