import asyncio
import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.enums.parse_mode import ParseMode

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "API_TOKEN = '7585234067:AAGNX-k10l5MuQ7nbMirlsls5jugil16V38')
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8101413562")

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

ULTIMO_ENVIO = ""

@dp.startup()
async def iniciar(_):
    print("[BOT] Telegram iniciado")

async def enviar_sinais():
    global ULTIMO_ENVIO
    while True:
        try:
            with open("sinais.json") as f:
                sinais = json.load(f)
            if sinais:
                novo = sinais[-1]
                if novo["timestamp"] != ULTIMO_ENVIO:
                    msg = f"📡 <b>NOVO SINAL DETECTADO</b>

🎯 <b>Multiplicador:</b> <code>{novo['valor']}x</code>
🏷️ <b>Tipo:</b> {novo['tipo']}
🕒 <b>Hora:</b> {novo['timestamp']}"
                    await bot.send_message(CHAT_ID, msg)
                    ULTIMO_ENVIO = novo["timestamp"]
        except Exception as e:
            print(f"[ERRO BOT] {e}")
        await asyncio.sleep(15)

async def iniciar_bot():
    asyncio.create_task(enviar_sinais())
    await dp.start_polling(bot)
