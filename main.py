import os
import asyncio
import requests
from datetime import datetime
from tapo import ApiClient

TP_EMAIL = os.environ["TP_EMAIL"]
TP_PASSWORD = os.environ["TP_PASSWORD"]
TP_DEVICE_ID = os.environ["TP_DEVICE_ID"]

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

CHECK_INTERVAL = 60
last_state = None


def send(text: str):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text},
        timeout=10
    )


async def check():
    global last_state

    client = ApiClient(TP_EMAIL, TP_PASSWORD)

    # ⬇️ ГОЛОВНЕ: отримуємо пристрій НАПРЯМУ по device_id
    device = await client.get_device_by_id(TP_DEVICE_ID)

    while True:
        try:
            await device.get_device_info()
            state = "on"
        except Exception:
            state = "off"

        if state != last_state:
            now = datetime.now().strftime("%H:%M")
            if state == "on":
                send(f"💡 Світло ЗʼЯВИЛОСЬ ({now})")
            else:
                send(f"🚫 Світло ЗНИКЛО ({now})")
            last_state = state

        await asyncio.sleep(CHECK_INTERVAL)


asyncio.run(check())
