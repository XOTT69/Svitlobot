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

# ================== ENV ==================
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
TAPO_EMAIL = os.environ["TAPO_USERNAME"]
TAPO_PASSWORD = os.environ["TAPO_PASSWORD"]

# ================== TIME ==================
def kyiv_time():
    return datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%H:%M")

# ================== TP-LINK CLOUD ==================
CLOUD_URL = "https://eu-wap.tplinkcloud.com"
cloud_token = None
device_id = None
last_state = None
power_off_at = None


def tp_login():
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


def fetch_device():
    global device_id
    r = requests.post(f"{CLOUD_URL}/?token={cloud_token}",
        json={"method": "getDeviceList"}, timeout=15
    ).json()
    for d in r["result"]["deviceList"]:
        if "PLUG" in d.get("deviceType", "").upper():
            device_id = d["deviceId"]
            return


def power_present():
    try:
        r = requests.post(f"{CLOUD_URL}/?token={cloud_token}", json={
            "method": "passthrough",
            "params": {
                "deviceId": device_id,
                "requestData": '{"method":"get_device_info"}'
            }
        }, timeout=10).json()
        return True
    except:
        return False


# ================== DTEK FILTER ==================
def build_22_message(text: str):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return None
    header = lines[0]
    for l in lines:
        if "2.2" in l and ("Підгрупа" in l or "підгрупу" in l):
            return f"{header}\n\n📍 {l}"
    return None


# ================== HANDLERS ==================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or update.message.caption or ""
    msg = build_22_message(text)
    if msg:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)


async def power_loop(app):
    global last_state, power_off_at
    while True:
        state = power_present()
        if state != last_state:
            now = kyiv_time()
            if not state:
                power_off_at = time.time()
                await app.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=f"⚡ Світло зникло — {now}"
                )
            else:
                mins = int((time.time() - power_off_at) / 60) if power_off_at else 0
                await app.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=f"🔌 Світло зʼявилось — {now}\n⏱️ Не було: {mins} хв"
                )
            last_state = state
        await asyncio.sleep(60)


# ================== MAIN ==================
async def main():
    print("🚀 SVITLOBOT START")

    tp_login()
    fetch_device()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(
        (filters.TEXT | filters.CAPTION) & ~filters.COMMAND,
        handle_message
    ))

    asyncio.create_task(power_loop(app))
    await app.run_polling(close_loop=False)


if __name__ == "__main__":
    asyncio.run(main())
