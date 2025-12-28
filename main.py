import os
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict

from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

app = FastAPI()
application = None

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
    print("🔌 TP-Link...")
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
    for d in r["result"]["deviceList"]:
        if "PLUG" in d.get("deviceType", "").upper():
            device_id = d["deviceId"]
            print(f"✅ P110: {d.get('nickname', 'Unknown')}")
            return True
    return False

def power_present():
    if not device_id: return True
    try:
        r = requests.post(f"{CLOUD_URL}/?token={cloud_token}", json={
            "method": "passthrough", "params": {
                "deviceId": device_id, "requestData": '{"method":"get_device_info"}'
            }
        }, timeout=10).json()
        data = r["result"]["responseData"]
        power = data.get("current_power", 0) / 1000  # mW → W
        print(f"🔌 P110: {power:.1f}W")
        return power > 0.5  # >0.5W = світло
    except:
        return True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or update.message.caption or ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines: return
    header = lines[0]
    for line in lines:
        if "2.2" in line and ("Підгрупа" in line or "підгрупу" in line):
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"{header}\n\n📍 {line}")

async def power_job(context: ContextTypes.DEFAULT_TYPE):
    global last_state, power_off_at
    state = power_present()
    
    if state == last_state: return
    
    now = kyiv_time()
    if not state:
        power_off_at = time.time()
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"⚡ Світло зникло — {now}")
    else:
        minutes = int((time.time() - power_off_at) / 60) if power_off_at else 0
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"🔌 Світло зʼявилось — {now}\n⏱️ Не було: {minutes} хв")
    
    last_state = state

@app.on_startup
async def startup():
    global application
    print("🚀 STARTUP...")
    
    cloud_login()
    fetch_device_id()
    
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )
    
    application.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, handle_message))
    application.job_queue.run_repeating(power_job, interval=30, first=10)
    
    # WEBHOOK
    webhook_url = f"https://{os.getenv('RAILWAY_STATIC_URL')}/webhook"
    await application.bot.set_webhook(webhook_url)
    print(f"✅ Webhook: {webhook_url}")

@app.post("/webhook")
async def webhook(request: Request):
    update = Update.de_json(await request.json(), application.bot)
    await application.process_update(update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"status": "SvitloBot P110 OK"}
