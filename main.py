import os
import asyncio
from datetime import datetime
import requests
from tapo import ApiClient

TP_EMAIL = os.environ["TP_EMAIL"]
TP_PASSWORD = os.environ["TP_PASSWORD"]
TP_DEVICE_ID = os.environ["TP_DEVICE_ID"]

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

CHECK_INTERVAL = 60  # секунд
last_state = None

def send(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text}
    )

async def check():
    global last_state

    client = ApiClient(TP_EMAIL, TP_PASSWORD)
    devices = await client.devices()

    device = next(d for d in devices if d.device_id == TP_DEVICE_ID)

    while True:
        try:
            await device.get_device_info()
            state = "on"
        except Exception:
            state = "off"

        if state != last_state:
            t = datetime.now().strftime("%H:%M")
            if state == "on":
                send(f"💡 Світло ЗʼЯВИЛОСЬ ({t})")
            else:
                send(f"🚫 Світло ЗНИКЛО ({t})")
            last_state = state

        await asyncio.sleep(CHECK_INTERVAL)

asyncio.run(check())
