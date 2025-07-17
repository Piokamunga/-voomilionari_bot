""" telegrambotpy.py – VOO MILIONÁRIO Bot (Telegram + Webhook + IA) """

import os
import aiohttp
import asyncio
from datetime import datetime
from aiohttp import web

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from analisador_ia import analisar_multiplicadores

# === CONFIGURAÇÕES ===
TOKEN = "7585234067:AAF1xfSbMCh7LOckXViD2_iUfKig7GYgwO4"
GROUP_ID = -1002769928832  # Grupo VOO MILIONÁRIO
WEBHOOK_DOMAIN = "https://voomilionari-bot.onrender.com"
WEBHOOK_PATH = "/webhook"

# === BOT E DISPATCHER ===
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# === ENVIO DE SINAL PARA O TELEGRAM ===
async def enviar_sinal(mensagem: str):
    try:
        await bot.send_message(chat_id=GROUP_ID, text=mensagem)
    except Exception as e:
        print(f"[ERRO Telegram] {e}")

# === COMANDO /start ===
@dp.message(F.text == "/start")
async def start_handler(message: Message):
    await message.answer("🚀 Bot VOO MILIONÁRIO ativo com IA!")

# === LOOP DE ANÁLISE COM IA ===
async def loop_analise():
    while True:
        try:
            arquivos = sorted(os.listdir("logs"), reverse=True)
            for nome in arquivos:
                if nome.endswith(".html"):
                    with open(f"logs/{nome}", "r", encoding="utf-8") as f:
                        html = f.read()
                    resposta = analisar_multiplicadores(html)
                    if resposta:
                        await enviar_sinal(resposta)
                    break
        except Exception as e:
            print(f"[ERRO análise IA] {e}")
        await asyncio.sleep(10)

# === INICIAR SERVIDOR WEBHOOK ===
async def iniciar_bot():
    app = web.Application()
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    setup_application(app, dp, bot=bot, route=WEBHOOK_PATH)
    
    await bot.set_webhook(f"{WEBHOOK_DOMAIN}{WEBHOOK_PATH}")
    
    app.on_startup.append(lambda app: asyncio.create_task(loop_analise()))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=8080)
    await site.start()
