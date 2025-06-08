import asyncio
import os
import json
from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7585234067:AAGNX-k10l5MuQ7nbMirlsls5jugil16V38")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "8101413562"))
GRUPO_ID = int(os.getenv("TELEGRAM_GROUP_ID", "-1002769928832"))  # Adicione seu grupo aqui

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

ULTIMO_ENVIO = ""

async def enviar_sinal(jogo, multiplicador, hora):
    msg = (
        f"📡 <b>NOVO SINAL DETECTADO</b>\n\n"
        f"🎯 <b>Jogo:</b> {jogo}\n"
        f"📈 <b>Multiplicador:</b> <code>{multiplicador}x</code>\n"
        f"⏱️ <b>Hora:</b> {hora}\n\n"
        f"⚡ Prepare-se para a próxima entrada!\n"
        f"🎰 <a href='https://bit.ly/449TH4F'>Acesse o Jogo Agora</a>\n"
    )

    try:
        await bot.send_message(CHAT_ID, msg, disable_web_page_preview=True)
        await bot.send_message(GRUPO_ID, msg, disable_web_page_preview=True)
        print(f"[+] Sinal enviado com sucesso: {jogo} - {multiplicador}x - {hora}")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar sinal: {e}")

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
                    # Supondo que o JSON tenha esses campos:
                    jogo = novo.get("jogo", "Desconhecido")
                    multiplicador = novo.get("valor", "N/A")
                    hora = novo.get("timestamp", "N/A")

                    await enviar_sinal(jogo, multiplicador, hora)
                    ULTIMO_ENVIO = novo["timestamp"]
        except Exception as e:
            print(f"[ERRO BOT] {e}")
        await asyncio.sleep(15)

async def iniciar_bot():
    asyncio.create_task(enviar_sinais())
    await dp.start_polling(bot)
