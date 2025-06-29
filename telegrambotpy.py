"""
telegrambotpy.py — Voo Milionário Bot
Monitora o Aviator 24/7 e envia sinais ≥ 1.99 x no Telegram.

Requisitos:
• Python ≥ 3.11  • aiogram 3.x
• aiohttp • pytz • matplotlib
• (.env) TG_BOT_TOKEN, GB_USERNAME, GB_PASSWORD
Autor: Pio Ginga (2025)
"""

# =========================
# IMPORTS
# =========================
import os
import re
import json
import socket
import asyncio
import aiohttp
import pytz
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import List, Tuple

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
    BotCommand,
)
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# =========================
# VARIÁVEIS DE AMBIENTE
# =========================
load_dotenv()

TOKEN      = os.getenv("TG_BOT_TOKEN")
CHAT_ID    = os.getenv("CHAT_ID", "8101413562")
GRUPO_ID   = os.getenv("GRUPO_ID", "-1002769928832")
USERNAME   = os.getenv("GB_USERNAME")
PASSWORD   = os.getenv("GB_PASSWORD")

if not all([TOKEN, USERNAME, PASSWORD]):
    raise RuntimeError("Defina TG_BOT_TOKEN, GB_USERNAME e GB_PASSWORD no .env")

LOGIN_URL = "https://m.goldenbet.ao/index/login"
GAME_URL  = "https://m.goldenbet.ao/gameGo?id=1873916590817091585&code=2201&platform=PP"

VELA_MINIMA = 1.99
VELA_RARA   = 100.0
LUANDA_TZ   = pytz.timezone("Africa/Luanda")

BANNER_LINK   = "https://bit.ly/449TH4F"
BANNER_IMAGEM = "https://i.ibb.co/ZcK9dcT/banner.png"

LOCK_FILE = ".bot_lock"
LOG_DIR   = "logs"
STATIC_DIR = "static"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

MENSAGENS_MOTIVAS: List[str] = [
    "💥 Hoje pode ser o dia da sua virada!",
    "🎯 O sucesso está nos detalhes. Foco total!",
    "🚀 Quem voa alto não tem medo da queda!",
    "📈 Persistência transforma tentativas em vitórias!",
    "🎲 O próximo voo pode ser o milionário!",
]

# =========================
# INSTÂNCIAS DO BOT
# =========================
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()
router = Router()
dp.include_router(router)

VELAS: List[float] = []
ULTIMO_MULT: float | None = None
ULTIMO_ENVIO_ID: str | None = None

# =========================
# FUNÇÕES AUXILIARES
# =========================
def checar_instancia() -> bool:
    """Evita múltiplas execuções usando arquivo-cadeado."""
    if os.path.exists(LOCK_FILE):
        print("⚠️ Bot já está em execução.")
        return False
    with open(LOCK_FILE, "w") as f:
        f.write(datetime.utcnow().isoformat())
    return True


def limpar_instancia() -> None:
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)


def salvar_log_sinal(sinal: dict) -> None:
    with open(f"{LOG_DIR}/sinais.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(sinal, ensure_ascii=False) + "\n")


def gerar_grafico(velas: List[float]) -> None:
    acertos = [1 if v >= VELA_MINIMA else 0 for v in velas]
    plt.figure(figsize=(10, 3))
    plt.plot(acertos, marker="o", linewidth=1)
    plt.title("Acertos (≥1.99x)")
    plt.grid(True, linestyle=":", linewidth=0.5)
    plt.tight_layout()
    plt.savefig(f"{STATIC_DIR}/chart.png")
    plt.close()

# ------------------------- Regex & Previsão ------------------
VELA_REGEX = re.compile(r"(\d+(?:\.\d+)?)[xX]")


def extrair_velas(html: str) -> List[float]:
    return [float(m.group(1)) for m in VELA_REGEX.finditer(html)]


def prever_proxima_entrada(seq: List[float]) -> Tuple[bool, float]:
    if len(seq) < 2:
        return False, 0.0
    if seq[-1] < 2.0 and seq[-2] < 2.0:
        chance = 90 + round((2.0 - seq[-1]) * 5 + (2.0 - seq[-2]) * 5, 1)
        return True, min(chance, 99.9)
    return False, 0.0

# =========================
# REQUISIÇÕES HTTP (aiohttp)
# =========================
async def login(session: aiohttp.ClientSession) -> bool:
    try:
        payload = {"account": USERNAME, "password": PASSWORD}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with session.post(LOGIN_URL, data=payload, headers=headers) as resp:
            ok = resp.status == 200
            print("[LOGIN]", "Sucesso" if ok else f"Falhou ({resp.status})")
            return ok
    except Exception as exc:
        print("[LOGIN EXCEPTION]", exc)
        return False


async def obter_html(session: aiohttp.ClientSession) -> str:
    try:
        async with session.get(GAME_URL, timeout=10) as resp:
            html = await resp.text()
            if "login" in html.lower():
                print("[HTML] Sessão expirada — refazendo login…")
                if await login(session):
                    return await obter_html(session)
                return ""
            return html
    except Exception as exc:
        print("[ERRO HTML]", exc)
        return ""

# =========================
# ENVIO DE SINAL & GRÁFICO
# =========================
async def enviar_sinal(sinal: dict) -> None:
    global ULTIMO_ENVIO_ID

    msg_id = f"{sinal['timestamp']}-{sinal['multiplicador']}"
    if msg_id == ULTIMO_ENVIO_ID:
        return
    ULTIMO_ENVIO_ID = msg_id

    texto = (
        "🎰 <b>SINAL DETECTADO - AVIATOR</b>\n\n"
        f"🕐 <b>Hora:</b> {sinal['hora']}\n"
        f"🎯 <b>Multiplicador:</b> <code>{sinal['multiplicador']}x</code>\n"
        f"📊 <b>Classificação:</b> {sinal['tipo']}\n"
        f"🔮 <b>Previsão:</b> {sinal['previsao']}\n\n"
        f"{sinal['mensagem'] or ''}\n\n"
        f"💰 Cadastre-se com bônus:\n👉 <a href='{BANNER_LINK}'>{BANNER_LINK}</a>"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Cadastre-se", url=BANNER_LINK)]
    ])

    for destino in (GRUPO_ID, CHAT_ID):
        try:
            await bot.send_photo(destino, photo=BANNER_IMAGEM, caption=texto, reply_markup=markup)
        except Exception as exc:
            print("[ERRO ENVIO]", exc)


async def enviar_grafico() -> None:
    gerar_grafico(VELAS)
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔗 Cadastre-se", url=BANNER_LINK)]]
    )
    for destino in (GRUPO_ID, CHAT_ID):
        try:
            await bot.send_photo(
                destino,
                photo=FSInputFile(f"{STATIC_DIR}/chart.png"),
                caption="📈 <b>Últimos acertos registrados</b>",
                reply_markup=markup,
            )
        except Exception as exc:
            print("[ERRO GRÁFICO]", exc)

# =========================
# HANDLERS TELEGRAM
# =========================
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🚀 Bot Voo Milionário online!\nUse /ajuda para ver todos os comandos."
    )

@router.message(Command("ajuda"))
async def cmd_ajuda(message: Message):
    await message.answer(
        "ℹ️ <b>Comandos</b>\n"
        "/start – Inicia o bot\n"
        "/ajuda – Mostra esta mensagem\n"
        "/grafico – Último gráfico de acertos\n"
        "/sinais – Últimos sinais\n"
        "/status – Dados internos\n"
        "/painel – Em breve\n"
        "/sobre – Sobre o projeto"
    )

@router.message(Command("grafico"))
async def cmd_grafico(message: Message):
    await enviar_grafico()

@router.message(Command("sinais"))
async def cmd_sinais(message: Message):
    path = f"{LOG_DIR}/sinais.jsonl"
    if not os.path.exists(path):
        await message.answer("Nenhum sinal registrado ainda.")
        return
    linhas = open(path, encoding="utf-8").read().strip().splitlines()[-5:]
    if not linhas:
        await message.answer("Nenhum sinal registrado ainda.")
        return
    itens = []
    for linha in linhas:
        d = json.loads(linha)
        itens.append(f"<b>{d['hora']}</b> — {d['multiplicador']}x ({d['tipo']})")
    await message.answer("📌 <b>Últimos sinais</b>:\n" + "\n".join(itens))

@router.message(Command("status"))
async def cmd_status(message: Message):
    await message.answer(
        f"📊 VELAS: {len(VELAS)}\n🔄 Último mult: {ULTIMO_MULT}\n💾 Último envio: {ULTIMO_ENVIO_ID}"
    )

@router.message(Command("painel"))
async def cmd_painel(message: Message):
    await message.answer("📊 Painel em construção. Acompanhe as atualizações!")

@router.message(Command("sobre"))
async def cmd_sobre(message: Message):
    await message.answer(
        "🤖 <b>Voo Milionário Bot</b> — monitora o Aviator em tempo real e envia sinais com base em dados reais."
    )

# =========================
# MONITORAMENTO LOOP
# =========================
async def monitorar() -> None:
    global VELAS, ULTIMO_MULT

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                html = await obter_html(session)
                if not html:
                    await asyncio.sleep(10)
                    continue

                velas = extrair_velas(html)
                if not velas:
                    await asyncio.sleep(10)
                    continue

                nova = velas[-1]
                if nova != ULTIMO_MULT:
                    VELAS.append(nova)
                    VELAS = VELAS[-20:]  # mantém só 20
                    ULTIMO_MULT = nova

                    hora = datetime.now(LUANDA_TZ).strftime("%H:%M:%S")
                    timestamp = datetime.utcnow().isoformat()
                    prever, chance = prever_proxima_entrada(VELAS)

                    tipo = "🔥 Alta (≥1.99x)" if nova >= VELA_MINIMA else "🢨 Baixa (<1.99x)"
                    mensagem = None
                    if nova >= VELA_RARA:
                        tipo = "🚀 Rara (>100x)"
                        mensagem = MENSAGENS_MOTIVAS[
                            int(datetime.now().timestamp()) % len(MENSAGENS_MOTIVAS)
                        ]

                    sinal = {
                        "hora": hora,
                        "multiplicador": nova,
                        "tipo": tipo,
                        "previsao": f"{chance}%" if prever else "Sem sinal",
                        "mensagem": mensagem,
                        "timestamp": timestamp,
                    }
                    salvar_log_sinal(sinal)
                    await enviar_sinal(sinal)

                await asyncio.sleep(5)

            except Exception as exc:
                print("[ERRO MONITOR]", exc)
                await asyncio.sleep(10)

# =========================
# COMANDOS BOT TELEGRAM
# =========================
async def registrar_comandos() -> None:
    comandos = [
        ("start", "Inicia o bot"),
        ("ajuda", "Ajuda e comandos"),
        ("sinais", "Últimos sinais"),
        ("grafico", "Gráfico de acertos"),
        ("status", "Dados internos"),
        ("painel", "Painel (em construção)"),
        ("sobre", "Sobre o bot"),
    ]
    await bot.set_my_commands([BotCommand(c, d) for c, d in comandos])
    print("[BOT] Comandos registrados")

# =========================
# INICIALIZAÇÃO
# =========================
async def iniciar_scraping() -> None:
    if not checar_instancia():
        return
    try:
        await registrar_comandos()
        asyncio.create_task(monitorar())
        await dp.start_polling(bot)
    finally:
        limpar_instancia()

# -------------------------
# ENTRADA PRINCIPAL
# -------------------------
if __name__ == "__main__":
    asyncio.run(iniciar_scraping())

    # --- Workaround Render free tier (porta obrigatória) ---
    if os.getenv("RENDER"):
        port = int(os.getenv("PORT", 10000))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", port))
            s.listen()
            print(f"[RENDER] Escutando porta {port} (fake listener)")
            s.accept()
