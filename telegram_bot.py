import asyncio
import json
import os
import re
import pytz
from datetime import datetime
import aiohttp
import matplotlib.pyplot as plt

from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

# === Configurações ===
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7585234067:AAGNX-k10l5MuQ7nbMirlsls5jugil16V38")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8101413562")
GRUPO_ID = os.getenv("TELEGRAM_GRUPO_ID", "-1002520564793")
URL = "https://m.goldenbet.ao/gameGo?id=1873916590817091585&code=2201&platform=PP"
VELA_MINIMA = 2.0
VELA_RARA = 100.0
LUANDA_TZ = pytz.timezone("Africa/Luanda")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

VELAS = []
ULTIMO_MULT = None
ULTIMO_ENVIO = None
CONTADOR = 0

# === Comando /start ===
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("🤖 Bot Aviator está online e monitorando as velas em tempo real!")

# === Funções principais ===
def prever_proxima_entrada(ultimas):
    if len(ultimas) < 2:
        return False, 0
    if ultimas[-1] < 2.0 and ultimas[-2] < 2.0:
        chance = 90 + round((2.0 - ultimas[-1]) * 5 + (2.0 - ultimas[-2]) * 5, 1)
        return True, min(chance, 99.9)
    return False, 0

async def obter_html(session):
    async with session.get(URL, timeout=10) as resp:
        return await resp.text()

def extrair_velas(html):
    padrao = r'<div class="result-item[^"]*">([^<]+)</div>'
    valores = re.findall(padrao, html)
    return [float(v.strip('x')) for v in valores if 'x' in v and v.replace("x", "").replace(".", "", 1).isdigit()]

async def enviar_sinal(sinal):
    texto = (
        "🎰 <b>SINAL DETECTADO - AVIATOR</b>\n\n"
        f"🕐 <b>Hora:</b> {sinal['hora']}\n"
        f"🎯 <b>Multiplicador:</b> <code>{sinal['multiplicador']}x</code>\n"
        f"📊 <b>Classificação:</b> {sinal['tipo']}\n"
        f"🔮 <b>Previsão:</b> {sinal['previsao']}\n\n"
    )
    if sinal["mensagem"]:
        texto += f"{sinal['mensagem']}\n\n"

    texto += "💰 Cadastre-se com bônus:\n👉 <a href='https://bit.ly/449TH4F'>https://bit.ly/449TH4F</a>"

    try:
        await bot.send_message(GRUPO_ID, texto)
        await bot.send_message(CHAT_ID, texto)
    except Exception as e:
        print(f"[ERRO ENVIO] {e}")

def gerar_grafico_acertos(velas):
    acertos = [1 if v >= VELA_MINIMA else 0 for v in velas]
    plt.figure(figsize=(10, 3))
    plt.plot(acertos, marker='o', linestyle='-', color='green')
    plt.title("Gráfico de Acertos (≥2x)")
    plt.xlabel("Rodadas")
    plt.ylabel("Acerto")
    plt.grid(True)
    plt.tight_layout()
    os.makedirs("static", exist_ok=True)
    plt.savefig("static/chart.png")
    plt.close()

async def enviar_grafico():
    try:
        gerar_grafico_acertos(VELAS)
        botao = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Cadastre-se com bônus", url="https://bit.ly/449TH4F")]
        ])
        for chat in [GRUPO_ID, CHAT_ID]:
            await bot.send_photo(
                chat,
                photo=types.FSInputFile("static/chart.png"),
                caption="📈 <b>Gráfico atualizado dos últimos sinais</b>",
                reply_markup=botao
            )
    except Exception as e:
        print(f"[ERRO GRAFICO] {e}")

async def iniciar_scraping():
    global VELAS, ULTIMO_MULT, ULTIMO_ENVIO, CONTADOR
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                html = await obter_html(session)
                velas = extrair_velas(html)
                if not velas:
                    await asyncio.sleep(10)
                    continue

                nova = velas[-1]
                if nova != ULTIMO_MULT:
                    VELAS.append(nova)
                    if len(VELAS) > 20:
                        VELAS.pop(0)

                    ULTIMO_MULT = nova
                    hora = datetime.now(LUANDA_TZ).strftime("%H:%M:%S")
                    ts = datetime.now().isoformat()
                    prever, chance = prever_proxima_entrada(VELAS)

                    tipo = "🔥 Alta (≥2x)" if nova >= VELA_MINIMA else "🧊 Baixa (<2x)"
                    if nova >= VELA_RARA:
                        tipo = "💎 Rara (≥100x)"

                    sinal = {
                        "jogo": "Aviator",
                        "multiplicador": f"{nova:.2f}",
                        "hora": hora,
                        "timestamp": ts,
                        "tipo": tipo,
                        "previsao": f"{chance:.1f}%" if prever else "Nenhuma",
                        "mensagem": (
                            "🚀 <b>Momento ideal para entrada!</b>\n"
                            f"🎯 Aposte na próxima rodada com confiança.\n"
                            f"📈 Chance estimada: <b>{chance:.1f}%</b>"
                        ) if prever else None
                    }

                    if sinal != ULTIMO_ENVIO:
                        await enviar_sinal(sinal)
                        ULTIMO_ENVIO = sinal
                        CONTADOR += 1

                        # A cada 10 sinais, envia gráfico
                        if CONTADOR % 10 == 0:
                            await enviar_grafico()

            except Exception as e:
                print(f"[ERRO SCRAPER] {e}")
            await asyncio.sleep(10)

# === Inicializador principal ===
async def main():
    await asyncio.gather(
        dp.start_polling(bot),
        iniciar_scraping()
    )

if __name__ == "__main__":
    asyncio.run(main())
