import os
import re
import json
import asyncio
import aiohttp
import pytz
import matplotlib.pyplot as plt
from datetime import datetime
from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# === VARIÁVEIS DE AMBIENTE ===
load_dotenv()
TOKEN = os.getenv("TG_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID") or "8101413562"
GRUPO_ID = os.getenv("GRUPO_ID") or "-1002769928832"

USERNAME = os.getenv("GB_USERNAME")
PASSWORD = os.getenv("GB_PASSWORD")
LOGIN_URL = "https://m.goldenbet.ao/index/login"
GAME_URL = "https://m.goldenbet.ao/gameGo?id=1873916590817091585&code=2201&platform=PP"

VELA_MINIMA, VELA_RARA = 2.0, 100.0
LUANDA_TZ = pytz.timezone("Africa/Luanda")
banner_link = "https://bit.ly/449TH4F"
banner_imagem = "https://i.ibb.co/ZcK9dcT/banner.png"

MENSAGENS_MOTIVAS = [
    "💥 Hoje pode ser o dia da sua virada!",
    "🎯 O sucesso está nos detalhes. Foco total!",
    "🚀 Quem voa alto não tem medo da queda!",
    "📈 Persistência transforma tentativas em vitórias!",
    "🎲 O próximo voo pode ser o milionário!"
]
LOCK_FILE, LOG_DIR = ".bot_lock", "logs"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

# === INSTÂNCIAS ===
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)
VELAS, ULTIMO_MULT, ULTIMO_ENVIO_ID = [], None, None

# === FUNÇÕES ===
def checar_instancia():
    if os.path.exists(LOCK_FILE):
        print("⚠️ Bot já está em execução."); return False
    with open(LOCK_FILE, "w") as f:
        f.write(str(datetime.utcnow())); return True

def limpar_instancia():
    if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)

def salvar_log_sinal(sinal: dict):
    with open(f"{LOG_DIR}/sinais.jsonl", "a") as f:
        f.write(json.dumps(sinal, ensure_ascii=False)+"\n")

def gerar_grafico(velas):
    acertos = [1 if v >= VELA_MINIMA else 0 for v in velas]
    plt.figure(figsize=(10,3))
    plt.plot(acertos, marker='o', color='green')
    plt.title("Acertos (≥2x)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("static/chart.png")
    plt.close()

def extrair_velas(html):
    padrao = r'<div class="result-item[^"]*">([^<]+)</div>'
    return [float(v.strip().lower().replace('x','')) for v in re.findall(padrao, html) if v.strip().replace('x','').replace('.','').isdigit()]

def prever_proxima_entrada(ultimas):
    if len(ultimas) < 2: return False, 0
    if ultimas[-1] < 2.0 and ultimas[-2] < 2.0:
        chance = 90 + round((2.0 - ultimas[-1]) * 5 + (2.0 - ultimas[-2]) * 5, 1)
        return True, min(chance, 99.9)
    return False, 0

# === REQUISIÇÕES ===
async def login(session):
    try:
        payload = {"account": USERNAME, "password": PASSWORD}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with session.post(LOGIN_URL, data=payload, headers=headers) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[LOGIN EXCEPTION] {e}"); return False

async def obter_html(session):
    if not await login(session): return ""
    try:
        async with session.get(GAME_URL, timeout=10) as resp:
            html = await resp.text()
            return html if "login" not in html.lower() else ""
    except Exception as e:
        print(f"[ERRO HTML] {e}"); return ""

async def enviar_sinal(sinal):
    global ULTIMO_ENVIO_ID
    msg_id = f"{sinal['timestamp']}-{sinal['multiplicador']}"
    if msg_id == ULTIMO_ENVIO_ID: return
    ULTIMO_ENVIO_ID = msg_id

    texto = (
        "🎰 <b>SINAL DETECTADO - AVIATOR</b>\n\n"
        f"🕐 <b>Hora:</b> {sinal['hora']}\n"
        f"🎯 <b>Multiplicador:</b> <code>{sinal['multiplicador']}x</code>\n"
        f"📊 <b>Classificação:</b> {sinal['tipo']}\n"
        f"🔮 <b>Previsão:</b> {sinal['previsao']}\n\n"
        f"{sinal['mensagem'] or ''}\n\n"
        f"💰 Cadastre-se com bônus:\n👉 <a href='{banner_link}'>{banner_link}</a>"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔗 Cadastre-se", url=banner_link)]])

    try:
        await bot.send_photo(GRUPO_ID, photo=banner_imagem, caption=texto, reply_markup=markup)
        await bot.send_photo(CHAT_ID, photo=banner_imagem, caption=texto, reply_markup=markup)
        print(f"[SINAL] Enviado: {sinal['multiplicador']}x às {sinal['hora']}")
    except Exception as e:
        print(f"[ERRO ENVIO] {e}")

async def enviar_grafico():
    try:
        gerar_grafico(VELAS)
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔗 Cadastre-se", url=banner_link)]])
        for chat in [GRUPO_ID, CHAT_ID]:
            await bot.send_photo(chat, photo=FSInputFile("static/chart.png"), caption="📈 <b>Últimos acertos registrados</b>", reply_markup=markup)
        print("[GRÁFICO] Enviado com sucesso")
    except Exception as e:
        print(f"[ERRO GRAFICO] {e}")

# === HANDLERS ===
@router.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🚀 Bot Voo Milionário está online e monitorando o Aviator em tempo real!")

@router.message(Command("grafico"))
async def grafico_handler(message: Message):
    await enviar_grafico()

# === MONITORAMENTO ===
async def monitorar():
    global VELAS, ULTIMO_MULT
    async with aiohttp.ClientSession() as session:
        while True:
            html = await obter_html(session)
            if not html:
                await asyncio.sleep(10); continue

            velas_atual = extrair_velas(html)
            if not velas_atual:
                await asyncio.sleep(10); continue

            nova = velas_atual[-1]
            if nova != ULTIMO_MULT:
                VELAS.append(nova)
                if len(VELAS) > 20: VELAS.pop(0)
                ULTIMO_MULT = nova

                hora = datetime.now(LUANDA_TZ).strftime("%H:%M:%S")
                timestamp = datetime.utcnow().isoformat()
                prever, chance = prever_proxima_entrada(VELAS)

                tipo = "🔥 Alta (≥2x)" if nova >= VELA_MINIMA else "🢨 Baixa (<2x)"
                mensagem = None
                if nova >= VELA_RARA:
                    tipo = "🚀 Rara (>100x)"
                    mensagem = MENSAGENS_MOTIVAS[datetime.now().second % len(MENSAGENS_MOTIVAS)]

                sinal = {
                    "hora": hora,
                    "multiplicador": nova,
                    "tipo": tipo,
                    "previsao": f"{chance}%" if prever else "Sem sinal",
                    "mensagem": mensagem,
                    "timestamp": timestamp
                }
                salvar_log_sinal(sinal)
                await enviar_sinal(sinal)

            await asyncio.sleep(5)

# === INICIALIZAÇÃO ===
async def iniciar_scraping():
    if not checar_instancia(): return
    try:
        asyncio.create_task(monitorar())
        await dp.start_polling(bot)
    finally:
        limpar_instancia()

if __name__ == "__main__":
    asyncio.run(iniciar_scraping())
