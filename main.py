import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes, 
    MessageHandler, CommandHandler, filters
)
from tapo import ApiClient

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = -1003534080985
TAPO_USERNAME = os.getenv("TAPO_USERNAME")
TAPO_PASSWORD = os.getenv("TAPO_PASSWORD")
TAPO_IP = os.getenv("TAPO_IP")

# Глобальні змінні
tapo_client = None
tapo_device = None
last_state = None
monitoring_active = False

async def init_tapo():
    global tapo_client, tapo_device
    try:
        tapo_client = ApiClient(TAPO_USERNAME, TAPO_PASSWORD)
        tapo_device = await tapo_client.p110(TAPO_IP)
        print(f"✅ Tapo P110 {TAPO_IP} підключена!")
    except Exception as e:
        print(f"❌ Помилка Tapo: {e}")

async def get_light_status() -> str:
    try:
        if not tapo_device:
            return "❌ Tapo недоступна"
        info = await tapo_device.get_device_info()
        state = info.device_state.state
        return "Світло є ✅" if state else "Світла нема ❌"
    except:
        return "❌ Помилка перевірки статусу"

async def light_on():
    try:
        if tapo_device:
            await tapo_device.on()
            return True
    except:
        pass
    return False

async def light_off():
    try:
        if tapo_device:
            await tapo_device.off()
            return True
    except:
        pass
    return False

async def monitor_light(context: ContextTypes.DEFAULT_TYPE):
    """Авто-моніторинг кожні 30 сек"""
    global last_state
    try:
        status = await get_light_status()
        current_state = "Світло є ✅" in status
        
        if last_state is not None and current_state != last_state:
            change_msg = "💡 Світло з'явилось! ✅" if current_state else "💡 Світло зникло! ❌"
            await context.bot.send_message(chat_id=CHANNEL_ID, text=change_msg)
            print(f"🔔 Авто-сповіщення: {change_msg}")
        
        last_state = current_state
    except Exception as e:
        print(f"⚠️ Моніторинг помилка: {e}")

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

    line_22 = None
    for line in lines:
        if "2.2" in line and "підгрупу" in line:
            line_22 = line
            break

    if line_22:
        if line_22 == header:
            return line_22
        return f"{header}\n{line_22}"
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    text = msg.text or msg.caption or ""
    if not text:
        return
    payload = build_22_message(text)
    if payload:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=payload)

# Команди
async def cmd_light_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = await get_light_status()
    await update.message.reply_text(status)
    await context.bot.send_message(chat_id=CHANNEL_ID, text=status)

async def cmd_light_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    success = await light_on()
    status = await get_light_status()
    msg = f"🔌 ВКЛ / {status}" if success else f"❌ Не вдалось / {status}"
    await update.message.reply_text(msg)
    await context.bot.send_message(chat_id=CHANNEL_ID, text=status)

async def cmd_light_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    success = await light_off()
    status = await get_light_status()
    msg = f"🔌 ВИКЛ / {status}" if success else f"❌ Не вдалось / {status}"
    await update.message.reply_text(msg)
    await context.bot.send_message(chat_id=CHANNEL_ID, text=status)

async def cmd_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global monitoring_active
    if not monitoring_active:
        monitoring_active = True
        context.job_queue.run_repeating(monitor_light, interval=30, first=5)
        await update.message.reply_text("👀 Моніторинг увімкнено!")
        print("👀 Моніторинг запущено")
    else:
        await update.message.reply_text("👀 Моніторинг вже працює")

async def post_init(application):
    await init_tapo()
    # АВТО-Запуск моніторингу при старті!
    global monitoring_active
    monitoring_active = True
    application.job_queue.run_repeating(monitor_light, interval=30, first=10)
    print("🚀 Авто-моніторинг запущено (кожні 30 сек)")

def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не знайдено!")
        return
    
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(MessageHandler((filters.TEXT | filters.CAPTION) & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("light", cmd_light_status))
    app.add_handler(CommandHandler("on", cmd_light_on))
    app.add_handler(CommandHandler("off", cmd_light_off))
    app.add_handler(CommandHandler("monitor", cmd_monitor))

    print("🚀 Бот з авто-моніторингом запущено!")
    print(f"📡 Розетка: {TAPO_IP}")
    app.run_polling()

if __name__ == "__main__":
    main()
