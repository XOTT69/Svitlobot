import asyncio
import os
from tapo import ApiClient
from telegram import Bot

TAPO_EMAIL = os.environ["TAPO_EMAIL"]
TAPO_PASSWORD = os.environ["TAPO_PASSWORD"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

CHECK_INTERVAL = 30
last_state = None

async def main():
    global last_state

    client = ApiClient(TAPO_EMAIL, TAPO_PASSWORD)

    devices = await client.get_devices()
    p110 = None

    for d in devices:
        if d.device_type == "SMART.PLUG":
            p110 = d
            break

    if not p110:
        raise Exception("P110 not found in Tapo account")

    device = await client.p110(p110.device_id)
    bot = Bot(BOT_TOKEN)

    while True:
        energy = await device.get_energy_usage()
        power = energy.current_power
        state = power > 0.5

        if state != last_state:
            if state:
                await bot.send_message(CHAT_ID, "💡 Світло зʼявилось")
            else:
                await bot.send_message(CHAT_ID, "🚫 Світло зникло")
            last_state = state

        await asyncio.sleep(CHECK_INTERVAL)

asyncio.run(main())
