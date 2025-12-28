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
CHANNEL_ID = -1003534080985

TAPO_EMAIL = os.environ["TAPO_USERNAME"]
TAPO_PASSWORD = os.environ["TAPO_PASSWORD"]
TAPO_REGION = "eu"

CHECK_INTERVAL = 60
# ============================================

CLOUD_URL = f"https://{TAPO_REGION}-wap.tplinkcloud.com"
cloud_token = None
device_id = None
last_power_state = None
power_off_at = None
app = None  # Глобальна змінна для бота


def kyiv_time():
    return datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%H:%M")


def cloud_login():
    global cloud_token
    r = requests.post(f"{CLOUD_URL}/", json={
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
    r = requests.post(f"{CLOUD_URL}/?token={cloud_token}", json={"method": "getDeviceList"}, timeout=15).json()
    devices = r["result"]["deviceList"]
    for d in devices:
        if "PLUG" in (d.get("deviceType") or "").upper():
            device_id = d["deviceId"]
            return
    if devices:
        device_id = devices[0]["deviceId"]
    else:
        raise RuntimeError("Tapo пристрої не знайдені")


def power_present() -> bool:
    try:
        r = requests.post(f"{CLOUD_URL}/?token={cloud_token}", json={
            "method": "passthrough",
            "params": {
                "deviceId": device_id,
                "requestData": '{"method":"get_device_info"}'
            }
        }, timeout=15).json()
        return bool(r["result"]["responseData"])
    except:
        return False


def build_22_message(text: str) -> str | None:
    lines = text.splitlines()
    header = next((line for line in lines if line.strip()), None)
    if not header:
        return None

    start_22 = next((i for i, line in enumerate(lines) if "Підгрупа" in line and "2.2" in line), None)
    if start_22 is not None:
        block = [l for l in lines[start_22:] if l.strip()][:10]  # обмежуємо
        header_lines = [lines[i] for i in range(len(lines)) if lines[i].strip()][:2]
        return "\n".join(header_lines + [""] + block).strip()

    for line in lines:
        if "2.2" in line and "підгрупу" in line:
            return f"{header}\n{line}"
    return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or update.message.caption or ""
    if not text:
        return

    payload = build_22_message(text)
    if payload:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=payload)


async def power_checker():
    """✅ Автономна перевірка світла без job_queue"""
    global last_power_state, power_off_at
    
    while True:
        try:
            state = power_present()
            if state != last_power_state:
                now = kyiv_time()
                if not state:
                    power_off_at = time.time()
                    await app.bot.send_message(chat_id=CHANNEL_ID, text=f"⚡ Світло зникло — {now}")
                else:
                    minutes = int((time.time() - power_off_at) / 60) if power_off_at else 0
                    await app.bot.send_message(chat_id=CHANNEL_ID, text=f"🔌 Світло зʼявилось — {now}\n⏱️ Не було: {minutes} хв")
                last_power_state = state
        except Exception as e:
            print(f"Помилка перевірки: {e}")
        
        await asyncio.sleep(CHECK_INTERVAL)


async def main():
    global app
    
    cloud_login()
    fetch_device_id()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, handle_message))
    
    # ✅ Запускаємо перевірку світла паралельно
    asyncio.create_task(power_checker())
    
    print(f"🚀 Бот запущено. Перевірка кожні {CHECK_INTERVAL}с")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
