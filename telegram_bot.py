import asyncio
import os
import json
import random
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7585234067:AAGNX-k10l5MuQ7nbMirlsls5jugil16V38")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8101413562")
GRUPO_ID = os.getenv("TELEGRAM_GRUPO_ID", "-1002520564793")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

ULTIMO_ENVIO = None

def gerar_sinal():
    jogos = ["Aviator", "Crash", "Double", "Mines"]
    return {
        "jogo": random.choice(jogos),
        "multiplicador": round(random.uniform(2.0, 50.0), 2),
        "hora": datetime.now().strftime("%H:%M:%S"),
        "timestamp": datetime.now().isoformat()
    }

async def salvar_novo_sinal():
    sinal = gerar_sinal()
    try:
        if not os.path.exists("sinais.json"):
            with open("sinais.json", "w") as f:
                json.dump([], f)
        with open("sinais.json", "r") as f:
            sinais = json.load(f)
        sinais.append(sinal)
        with open("sinais.json", "w") as f:
            json.dump(sinais, f, indent=2)
    except Exception as e:
        print(f"[ERRO] Falha ao salvar sinal: {e}")
    return sinal

async def enviar_sinais():
    global ULTIMO_ENVIO
    while True:
        novo_sinal = await salvar_novo_sinal()
        if novo_sinal["timestamp"] != ULTIMO_ENVIO:
            msg = (
                f"📡 <b>NOVO SINAL DETECTADO</b>\n\n"
                f"🎯 <b>Jogo:</b> {novo_sinal['jogo']}\n"
                f"📈 <b>Multiplicador:</b> <code>{novo_sinal['multiplicador']}x</code>\n"
                f"⏱️ <b>Hora:</b> {novo_sinal['hora']}\n\n"
                f"⚡ Prepare-se para a próxima entrada!\n"
                f"🎰 <a href='https://bit.ly/449TH4F'>Acesse o Jogo Agora</a>"
            )
            try:
                await bot.send_message(CHAT_ID, msg, disable_web_page_preview=True)
                await bot.send_message(GRUPO_ID, msg, disable_web_page_preview=True)
                print(f"[+] Sinal enviado: {novo_sinal}")
                ULTIMO_ENVIO = novo_sinal["timestamp"]
            except Exception as e:
                print(f"[ERRO] Falha ao enviar sinal: {e}")
        await asyncio.sleep(60)  # A cada 60 segundos

async def iniciar_bot():
    asyncio.create_task(enviar_sinais())
    await dp.start_polling(bot)
