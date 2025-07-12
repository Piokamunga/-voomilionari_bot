""" telegrambotpy.py – VOO MILIONÁRIO Bot (Telegram + Webhook + IA) """

import os
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from analisador_ia import analisar_multiplicadores
from aiohttp import web
from datetime import datetime

TOKEN = "7585234067:AAF1xfSbMCh7LOckXViD2_iUfKig7GYgwO4"
GROUP_ID = -1002769928832  # Grupo VOO MILIONÁRIO

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

async def enviar_sinal(mensagem: str):
    try:
        await bot.send_message(chat_id=GROUP_ID, text=mensagem)
    except Exception as e:
        print(f"[ERRO Telegram] {e}")

@dp.message(F.text == "/start")
async def start_handler(message: Message):
    await message.answer("🚀 Bot VOO MILIONÁRIO ativo com IA!")

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

async def iniciar_bot():
    app = web.Application()
    webhook_path = "/webhook"
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    setup_application(app, dp, bot=bot, route=webhook_path)
    await bot.set_webhook(f"https://https://voomilionari-bot.onrender.com{webhook_path}")  # Altere para seu domínio do Render
    app.on_startup.append(lambda app: asyncio.create_task(loop_analise()))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=8080)
    await site.start()
