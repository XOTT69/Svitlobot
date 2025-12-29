import os
import asyncio
from datetime import datetime
from tapo import ApiClient
import requests

TP_EMAIL = os.environ["TP_EMAIL"]
TP_PASSWORD = os.environ["TP_PASSWORD"]
TP_DEVICE_IP = os.environ["TP_DEVICE_IP"]

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

CHECK_INTERVAL = 60  # секунд

last_state = None

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

async def check():
    global last_state
    client = ApiClient(TP_EMAIL, TP_PASSWORD)
    device = await client.p110(TP_DEVICE_IP)

    while True:
        try:
            await device.get_device_info()
            state = "on"
        except:
            state = "off"

        if state != last_state:
            time = datetime.now().strftime("%H:%M")
            if state == "on":
                send(f"💡 Світло ЗʼЯВИЛОСЬ ({time})")
            else:
                send(f"🚫 Світло ЗНИКЛО ({time})")
            last_state = state

        await asyncio.sleep(CHECK_INTERVAL)

asyncio.run(check())
