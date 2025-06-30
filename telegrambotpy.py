"""
telegrambotpy.py — Voo Milionário Bot
Monitoramento 24/7 do Aviator; envia sinais ≥ 1.99 x para o Telegram.

Requisitos:
• Python ≥ 3.11 • aiogram 3.x • aiohttp • pytz • matplotlib
Variáveis (.env): TG_BOT_TOKEN, CHAT_ID, GRUPO_ID, (opcional) DEBUG=1
Autor: Pio Ginga – 2025
"""

# =========================================================
# IMPORTS
# =========================================================
from __future__ import annotations

import os, re, json, socket, asyncio
from datetime import datetime

import aiohttp, pytz, matplotlib.pyplot as plt
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

# =========================================================
# CONSTS & ENV
# =========================================================
load_dotenv()

TOKEN     = os.getenv("TG_BOT_TOKEN")
CHAT_ID   = os.getenv("CHAT_ID",  "8101413562")
GRUPO_ID  = os.getenv("GRUPO_ID", "-1002769928832")
DEBUG     = os.getenv("DEBUG", "0") == "1"   # define DEBUG=1 no .env p/ ver HTML

GAME_URL = (
    "https://m.goldenbet.ao/gameGo"
    "?id=1873916590817091585&code=2201&platform=PP"
)

VELA_MINIMA = 1.99
VELA_RARA   = 100.0
LUANDA_TZ   = pytz.timezone("Africa/Luanda")

BANNER_LINK   = "https://bit.ly/449TH4F"
BANNER_IMAGEM = "https://i.ibb.co/ZcK9dcT/banner.png"

MENSAGENS_MOTIVAS = [
    "💥 Hoje pode ser o dia da sua virada!",
    "🎯 O sucesso está nos detalhes. Foco total!",
    "🚀 Quem voa alto não tem medo da queda!",
    "📈 Persistência transforma tentativas em vitórias!",
    "🎲 O próximo voo pode ser o milionário!",
]

LOCK_FILE  = ".bot_lock"
LOG_DIR    = "logs"
STATIC_DIR = "static"
os.makedirs(LOG_DIR,    exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# =========================================================
# BOT / ROUTER
# =========================================================
bot    = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp     = Dispatcher()
router = Router()
dp.include_router(router)

VELAS: list[float]        = []
ULTIMO_MULT: float | None = None
ULTIMO_ENVIO_ID: str  | None = None

# =========================================================
# AUX
# =========================================================
def checar_instancia() -> bool:
    """Impede múltiplas execuções em ambiente local/container único."""
    if os.path.exists(LOCK_FILE):
        print("⚠️  Bot já está em execução.")
        return False
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(datetime.utcnow().isoformat())
    return True


def limpar_instancia() -> None:
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)


def salvar_log_sinal(sinal: dict) -> None:
    with open(f"{LOG_DIR}/sinais.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(sinal, ensure_ascii=False) + "\n")


def gerar_grafico(velas: list[float]) -> None:
    acertos = [1 if v >= VELA_MINIMA else 0 for v in velas]
    plt.figure(figsize=(10, 3))
    plt.plot(acertos, marker="o", linewidth=1)
    plt.title("Acertos (≥1.99x)")
    plt.grid(True, linestyle=":", linewidth=0.5)
    plt.tight_layout()
    plt.savefig(f"{STATIC_DIR}/chart.png")
    plt.close()

# --------- Regex (suporta vírgula ou ponto) ---------
VELA_REGEX = re.compile(r"(\d+(?:[.,]\d+)?)[xX]")

def extrair_velas(html: str) -> list[float]:
    return [float(m.group(1).replace(',', '.')) for m in VELA_REGEX.finditer(html)]

def prever_proxima_entrada(hist: list[float]) -> tuple[bool, float]:
    if len(hist) < 2:
        return False, 0.0
    if hist[-1] < 2.0 and hist[-2] < 2.0:
        chance = 90 + round((2.0 - hist[-1]) * 5 + (2.0 - hist[-2]) * 5, 1)
        return True, min(chance, 99.9)
    return False, 0.0

# =========================================================
# HTTP
# =========================================================
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

async def obter_html(session: aiohttp.ClientSession) -> str:
    try:
        async with session.get(GAME_URL, headers=HEADERS, timeout=10) as resp:
            html = await resp.text()
            if DEBUG:
                print("[DEBUG] HTML len:", len(html))
                print("[DEBUG] Primeiros 300 chars:", html[:300])
            return html
    except Exception as exc:
        print("[ERRO HTML]", exc)
        return ""

# =========================================================
# ENVIO (sinal & gráfico)
# =========================================================
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
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔗 Cadastre-se", url=BANNER_LINK)]]
    )
    try:
        for dest in (GRUPO_ID, CHAT_ID):
            await bot.send_photo(dest, photo=BANNER_IMAGEM, caption=texto, reply_markup=markup)
        print(f"[SIGNAL] {sinal['multiplicador']}x às {sinal['hora']}")
    except Exception as exc:
        print("[ERRO ENVIO]", exc)

async def enviar_grafico() -> None:
    try:
        gerar_grafico(VELAS)
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔗 Cadastre-se", url=BANNER_LINK)]]
        )
        for dest in (GRUPO_ID, CHAT_ID):
            await bot.send_photo(
                dest,
                photo=FSInputFile(f"{STATIC_DIR}/chart.png"),
                caption="📈 <b>Histórico recente de acertos</b>",
                reply_markup=markup,
            )
        print("[GRÁFICO] Enviado")
    except Exception as exc:
        print("[ERRO GRÁFICO]", exc)

# =========================================================
# HANDLERS
# =========================================================
@router.message(Command("start"))
async def h_start(m: Message) -> None:
    await m.answer("🚀 Bot Voo Milionário online! Use /ajuda para comandos.")

@router.message(Command("grafico"))
async def h_grafico(m: Message) -> None:
    await enviar_grafico()

@router.message(Command("status"))
async def h_status(m: Message) -> None:
    txt = (
        f"📊 VELAS armazenadas: {len(VELAS)}\n"
        f"🔄 Último mult: {ULTIMO_MULT}\n"
        f"💾 Último envio: {ULTIMO_ENVIO_ID}"
    )
    await m.answer(txt)

@router.message(Command("ajuda"))
async def h_ajuda(m: Message) -> None:
    await m.answer(
        "ℹ️ <b>Comandos</b>\n"
        "/start – Inicia\n"
        "/grafico – Último gráfico\n"
        "/sinais – Últimos sinais\n"
        "/status – Info rápidas\n"
        "/sobre – Sobre o projeto"
    )

@router.message(Command("sinais"))
async def h_sinais(m: Message) -> None:
    log = f"{LOG_DIR}/sinais.jsonl"
    if not os.path.exists(log):
        await m.answer("Nenhum sinal registrado ainda.")
        return
    linhas = open(log, encoding="utf-8").read().strip().splitlines()[-5:]
    if not linhas:
        await m.answer("Nenhum sinal registrado ainda.")
        return
    itens = []
    for ln in linhas:
        d = json.loads(ln)
        itens.append(f"<b>{d['hora']}</b> — {d['multiplicador']}x ({d['tipo']})")
    await m.answer("📌 <b>Últimos sinais</b>:\n" + "\n".join(itens))

@router.message(Command("sobre"))
async def h_sobre(m: Message) -> None:
    await m.answer("🤖 Voo Milionário Bot – monitoramento 24/7 do Aviator.")

# =========================================================
# LOOP MONITOR
# =========================================================
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
                if DEBUG:
                    print("[DEBUG] Velas extraídas:", velas[-10:])
                if not velas:
                    await asyncio.sleep(10)
                    continue

                nova = velas[-1]
                if nova != ULTIMO_MULT:
                    VELAS.append(nova)
                    VELAS = VELAS[-20:]
                    ULTIMO_MULT = nova

                    hora = datetime.now(LUANDA_TZ).strftime("%H:%M:%S")
                    timestamp = datetime.utcnow().isoformat()
                    prever, chance = prever_proxima_entrada(VELAS)

                    tipo = "🔥 Alta (≥1.99x)" if nova >= VELA_MINIMA else "🢨 Baixa (<1.99x)"
                    mensagem = None
                    if nova >= VELA_RARA:
                        tipo = "🚀 Rara (>100x)"
                        idx = int(datetime.now().timestamp()) % len(MENSAGENS_MOTIVAS)
                        mensagem = MENSAGENS_MOTIVAS[idx]

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
                print("[ERRO LOOP]", exc)
                await asyncio.sleep(10)

# =========================================================
# REGISTRAR COMMANDS
# =========================================================
async def registrar_comandos() -> None:
    comandos = [
        ("start",   "Iniciar"),
        ("grafico", "Gráfico"),
        ("sinais",  "Últimos sinais"),
        ("status",  "Status"),
        ("ajuda",   "Ajuda"),
        ("sobre",   "Sobre"),
    ]
    await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in comandos])
    print("[BOT] Comandos registrados")

# =========================================================
# INIT
# =========================================================
async def iniciar_scraping() -> None:
    if not checar_instancia():
        return
    try:
        await registrar_comandos()
        asyncio.create_task(monitorar())
        await dp.start_polling(bot)
    finally:
        limpar_instancia()

# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    asyncio.run(iniciar_scraping())

    # Fake-listener para Render free tier
    if os.getenv("RENDER"):
        port = int(os.getenv("PORT", 10000))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", port))
            s.listen()
            print(f"[RENDER] Escutando porta {port} (fake listener)")
            s.accept()ddd
