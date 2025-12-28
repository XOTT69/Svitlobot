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
CHANNEL_ID = -1003534080985

TAPO_EMAIL = os.environ["TAPO_USERNAME"]
TAPO_PASSWORD = os.environ["TAPO_PASSWORD"]
TAPO_REGION = "eu"  # Україна

CHECK_INTERVAL = 60  # сек
# ============================================

CLOUD_URL = f"https://{TAPO_REGION}-wap.tplinkcloud.com"
cloud_token = None
device_id = None

last_power_state = None
power_off_at = None


# ---------- UTIL ----------
def kyiv_time():
    return datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%H:%M")


# ---------- TP-LINK CLOUD ----------
def cloud_login():
    global cloud_token
    r = requests.post(
        f"{CLOUD_URL}/",
        json={
            "method": "login",
            "params": {
                "appType": "Tapo_Android",
                "cloudUserName": TAPO_EMAIL,
                "cloudPassword": TAPO_PASSWORD,
                "terminalUUID": "svitlobot"
            }
        },
        timeout=10
    ).json()
    cloud_token = r["result"]["token"]


def fetch_device_id():
    global device_id
    r = requests.post(
        f"{CLOUD_URL}/?token={cloud_token}",
        json={"method": "getDeviceList"},
        timeout=10
    ).json()

    for d in r["result"]["deviceList"]:
        if d.get("deviceType") == "SMART.PLUG":
            device_id = d["deviceId"]
            return

    raise RuntimeError("Tapo P110 не знайдено")


def power_present() -> bool:
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

        # якщо відповідь є → розетка онлайн → є світло
        return bool(r["result"]["responseData"])
    except:
        return False


# ---------- 2.2 PARSER (ТВІЙ КОД) ----------
def build_22_message(text: str) -> str | None:
    lines = text.splitlines()

    header = None
    for line in lines:
        if line.strip():
            header = line
            break
    if header is None:
        return None

    start_22 = None
    for i, line in enumerate(lines):
        if "Підгрупа" in line and "2.2" in line:
            start_22 = i
            break

    if start_22 is not None:
        block = []
        for line in lines[start_22:]:
            if line.strip() == "" and block:
                break
            block.append(line)
        block = [l for l in block if l.strip()]

        header_lines = []
        for line in lines:
            if line.strip():
                header_lines.append(line)
            if len(header_lines) == 2:
                break

        result_lines = header_lines + [""] + block
        return "\n".join(result_lines).strip()

    for line in lines:
        if "2.2" in line and "підгрупу" in line:
            if line == header:
                return line
            return f"{header}\n{line}"

    return None


# ---------- MESSAGE HANDLER ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    text = msg.text or msg.caption or ""
    if not text:
        return

    payload = build_22_message(text)
    if not payload:
        return

    await context.bot.send_message(chat_id=CHANNEL_ID, text=payload)


# ---------- AUTO POWER CHECK ----------
async def power_job(context: ContextTypes.DEFAULT_TYPE):
    global last_power_state, power_off_at

    state = power_present()

    if state != last_power_state:
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
                text=(
                    f"🔌 Світло зʼявилось — {now}\n"
                    f"⏱️ Не було світла: {minutes} хв"
                )
            )

        last_power_state = state


# ---------- MAIN ----------
def main():
    cloud_login()
    fetch_device_id()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(
        (filters.TEXT | filters.CAPTION) & ~filters.COMMAND,
        handle_message,
    ))

    # авто-перевірка світла
    app.job_queue.run_repeating(power_job, interval=CHECK_INTERVAL, first=5)

    app.run_polling()


if __name__ == "__main__":
    main()
