import os
import json
import asyncio
from datetime import datetime
import pytz
from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.client.default import DefaultBotProperties

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7585234067:AAGNX-k10l5MuQ7nbMirlsls5jugil16V38")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8101413562")
GRUPO_ID = os.getenv("TELEGRAM_GRUPO_ID", "-1002520564793")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
ULTIMO_ENVIO = ""

LUANDA_TZ = pytz.timezone("Africa/Luanda")

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
                    hora_atual = datetime.now(LUANDA_TZ).strftime("%H:%M:%S")
                    msg = (
                        f"📡 <b>NOVO SINAL DETECTADO</b>\n\n"
                        f"🎯 <b>Jogo:</b> {novo['jogo']}\n"
                        f"📈 <b>Multiplicador:</b> <code>{novo['multiplicador']}x</code>\n"
                        f"⏱️ <b>Hora:</b> {novo['hora']} (Luanda {hora_atual})\n\n"
                        f"⚡ Prepare-se para a próxima entrada!\n"
                        f"🎰 <a href='https://bit.ly/449TH4F'>Acesse o Jogo Agora</a>\n"
                    )
                    await bot.send_message(CHAT_ID, msg, disable_web_page_preview=True)
                    print(f"[+] Sinal enviado: {novo['jogo']} - {novo['multiplicador']}x - {hora_atual}")
                    ULTIMO_ENVIO = novo["timestamp"]
        except Exception as e:
            print(f"[ERRO] {e}")
        await asyncio.sleep(10)

async def watchdog():
    while True:
        agora = datetime.now(LUANDA_TZ).strftime("%H:%M:%S")
        print(f"[Watchdog] Bot está vivo - {agora} (Luanda)")
        await asyncio.sleep(300)  # 5 minutos

async def iniciar_bot():
    asyncio.create_task(enviar_sinais())
    asyncio.create_task(watchdog())
    await dp.start_polling(bot)
