import asyncio
import json
import os
import re
import pytz
from datetime import datetime
import aiohttp
import matplotlib.pyplot as plt

from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

# === Configurações ===
TOKEN = "7585234067:AAF1xfSbMCh7LOckXViD2_iUfKig7GYgwO4"  # VOOMILIONARIO_BOT
CHAT_ID = "8101413562"  # Seu chat pessoal
GRUPO_ID = "-1002769928832"  # Grupo VOO MILIONÁRIO

LOGIN_URL = "https://m.goldenbet.ao/index/login"
GAME_URL = "https://m.goldenbet.ao/gameGo?id=1873916590817091585&code=2201&platform=PP"

USERNAME = os.getenv("GB_USERNAME", "958752607")
PASSWORD = os.getenv("GB_PASSWORD", "958752607r")

VELA_MINIMA = 2.0
VELA_RARA = 100.0
LUANDA_TZ = pytz.timezone("Africa/Luanda")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

VELAS = []
ULTIMO_MULT = None
ULTIMO_ENVIO_ID = None
CONTADOR = 0

# === Comando inicial ===
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.reply("🚀 Bot Voo Milionário está online e monitorando o Aviator em tempo real!")

# === Previsão de entrada ===
def prever_proxima_entrada(ultimas):
    if len(ultimas) < 2:
        return False, 0
    if ultimas[-1] < 2.0 and ultimas[-2] < 2.0:
        chance = 90 + round((2.0 - ultimas[-1]) * 5 + (2.0 - ultimas[-2]) * 5, 1)
        return True, min(chance, 99.9)
    return False, 0

# === Login GoldenBet ===
async def login(session):
    try:
        payload = {"account": USERNAME, "password": PASSWORD}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with session.post(LOGIN_URL, data=payload, headers=headers) as resp:
            if resp.status == 200:
                print("[LOGIN] Login bem-sucedido.")
            else:
                print(f"[LOGIN ERRO] Código {resp.status}")
    except Exception as e:
        print(f"[LOGIN EXCEPTION] {e}")

# === Coleta da página do jogo ===
async def obter_html(session):
    try:
        await login(session)
        async with session.get(GAME_URL, timeout=10) as resp:
            return await resp.text()
    except Exception as e:
        print(f"[ERRO HTML] {e}")
        return ""

# === Extração das velas ===
def extrair_velas(html):
    padrao = r'<div class="result-item[^"]*">([^<]+)</div>'
    valores = re.findall(padrao, html)
    return [float(v.strip('x')) for v in valores if 'x' in v and v.replace("x", "").replace(".", "", 1).isdigit()]

# === Envio de sinal ===
async def enviar_sinal(sinal):
    global ULTIMO_ENVIO_ID

    texto = (
        "🎰 <b>SINAL DETECTADO - AVIATOR</b>\n\n"
        f"🕐 <b>Hora:</b> {sinal['hora']}\n"
        f"🎯 <b>Multiplicador:</b> <code>{sinal['multiplicador']}x</code>\n"
        f"📊 <b>Classificação:</b> {sinal['tipo']}\n"
        f"🔮 <b>Previsão:</b> {sinal['previsao']}\n\n"
        f"{sinal['mensagem'] or ''}\n\n"
        "💰 Cadastre-se com bônus:\n👉 <a href='https://bit.ly/449TH4F'>https://bit.ly/449TH4F</a>"
    )

    msg_id = f"{sinal['timestamp']}-{sinal['multiplicador']}"
    if msg_id == ULTIMO_ENVIO_ID:
        return  # Evita envio duplicado
    ULTIMO_ENVIO_ID = msg_id

    try:
        await bot.send_message(GRUPO_ID, texto)
        await bot.send_message(CHAT_ID, texto)
        print(f"[SINAL] Enviado: {sinal['multiplicador']}x às {sinal['hora']}")
    except Exception as e:
        print(f"[ERRO ENVIO] {e}")

# === Geração e envio de gráfico ===
def gerar_grafico(velas):
    acertos = [1 if v >= VELA_MINIMA else 0 for v in velas]
    plt.figure(figsize=(10, 3))
    plt.plot(acertos, marker='o', color='green')
    plt.title("Acertos (≥2x)")
    plt.grid(True)
    os.makedirs("static", exist_ok=True)
    plt.savefig("static/chart.png")
    plt.close()

async def enviar_grafico():
    try:
        gerar_grafico(VELAS)
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("🔗 Cadastre-se", url="https://bit.ly/449TH4F")]
        ])
        for chat in [GRUPO_ID, CHAT_ID]:
            await bot.send_photo(
                chat, photo=types.FSInputFile("static/chart.png"),
                caption="📈 <b>Últimos acertos registrados</b>", reply_markup=markup
            )
        print("[GRÁFICO] Enviado com sucesso")
    except Exception as e:
        print(f"[ERRO GRAFICO] {e}")

# === Loop principal ===
async def iniciar_monitoramento():
    global VELAS, ULTIMO_MULT, CONTADOR
    async with aiohttp.ClientSession() as session:
        while True:
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
                    "multiplicador": f"{nova:.2f}",
                    "hora": hora,
                    "timestamp": ts,
                    "tipo": tipo,
                    "previsao": f"{chance:.1f}%" if prever else "Nenhuma",
                    "mensagem": (
                        f"🚀 <b>Chance alta!</b>\nAposte com confiança.\n📈 Probabilidade: <b>{chance:.1f}%</b>"
                        if prever else None
                    )
                }

                await enviar_sinal(sinal)
                CONTADOR += 1
                if CONTADOR % 10 == 0:
                    await enviar_grafico()
            await asyncio.sleep(10)

# === Execução ===
async def main():
    await asyncio.gather(
        dp.start_polling(bot),
        iniciar_monitoramento()
    )

if __name__ == "__main__":
    asyncio.run(main())
