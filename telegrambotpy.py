from __future__ import annotations
"""
telegrambotpy.py — Voo Milionário Bot (v2 – WebSocket)
────────────────────────────────────────────────────────
Monitoramento 24 h/dia do Aviator via **WebSocket oficial**; envia
sinais no Telegram sempre que o último multiplicador é ≥ 1 .99 x.

Requisitos mínimos
──────────────────
• Python ≥ 3.11  • aiogram 3.x  • websockets  • aiohttp  • pytz  • matplotlib

Variáveis (.env)
────────────────
TG_BOT_TOKEN   token do bot — obrigatório
CHAT_ID        chat‑admin (opcional, default 8101413562)
GRUPO_ID       grupo público (opcional, default -100…)
DEBUG          1 ativa logs extras (opcional)
SCRAPE_INTERVAL segundos entre tentativas de reconexão (default 5)

Autor : Pio Ginga (2025)
"""

# ╭────────────────────────────── imports ───────────────────────────────╮
import asyncio
import json
import os
import socket
from datetime import datetime

import matplotlib.pyplot as plt
import pytz
import websockets
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    BotCommand,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

# WebSocket helper (token + base URL)
from save_html_loop_ws import get_token, WS_BASE_URL  # type: ignore

# ╭────────────────────── configuração de ambiente ──────────────────────╮
load_dotenv()

TOKEN: str | None = os.getenv("TG_BOT_TOKEN")
CHAT_ID: str = os.getenv("CHAT_ID", "8101413562")
GRUPO_ID: str = os.getenv("GRUPO_ID", "-1002769928832")
DEBUG: bool = os.getenv("DEBUG", "0") == "1"

if not TOKEN:
    raise RuntimeError("Defina TG_BOT_TOKEN no .env!")

# WebSocket reconnect
RECONNECT_DELAY = int(os.getenv("SCRAPE_INTERVAL", "5"))

VELA_MINIMA = 1.99          # envia sinal ≥ 1.99 x
VELA_RARA   = 100.0         # classifica como rara
LUANDA_TZ   = pytz.timezone("Africa/Luanda")

BANNER_LINK = "https://bit.ly/449TH4F"
BANNER_IMG  = "https://i.ibb.co/ZcK9dcT/banner.png"

MENSAGENS_MOTIVAS: list[str] = [
    "💥 Hoje pode ser o dia da sua virada!",
    "🎯 O sucesso está nos detalhes. Foco total!",
    "🚀 Quem voa alto não tem medo da queda!",
    "📈 Persistência transforma tentativas em vitórias!",
    "🎲 O próximo voo pode ser o milionário!",
]

LOCK_FILE   = ".bot_lock"
LOG_DIR     = "logs"
STATIC_DIR  = "static"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# ╭─────────────────────────── bot & router ─────────────────────────────╮
bot    = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp     = Dispatcher()
router = Router()
dp.include_router(router)

# estado em memória
VELAS: list[float]        = []
ULTIMO_MULT: float | None = None
ULTIMO_ENVIO_ID: str | None = None

# ╭───────────────────────────── utils ──────────────────────────────────╮

def checar_instancia() -> bool:
    """Evita execuções simultâneas usando arquivo‑cadeado."""
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


def gerar_grafico(seq: list[float]) -> None:
    acertos = [1 if v >= VELA_MINIMA else 0 for v in seq]
    plt.figure(figsize=(10, 3))
    plt.plot(acertos, marker="o", linewidth=1)
    plt.title("Acertos (≥ 1.99 x)")
    plt.grid(True, linestyle=":", linewidth=0.5)
    plt.tight_layout()
    plt.savefig(f"{STATIC_DIR}/chart.png")
    plt.close()

# ╭────────────────────── previsão de entrada ───────────────────────────╮

def prever_proxima_entrada(seq: list[float]) -> tuple[bool, float]:
    if len(seq) < 2:
        return False, 0.0
    if seq[-1] < 2.0 and seq[-2] < 2.0:
        prob = 90 + round((2.0 - seq[-1]) * 5 + (2.0 - seq[-2]) * 5, 1)
        return True, min(prob, 99.9)
    return False, 0.0

# ╭─────────────────────── envio de mensagens ───────────────────────────╮
async def enviar_sinal(sinal: dict) -> None:
    global ULTIMO_ENVIO_ID
    msg_id = f"{sinal['timestamp']}-{sinal['multiplicador']}"
    if msg_id == ULTIMO_ENVIO_ID:
        return
    ULTIMO_ENVIO_ID = msg_id

    texto = (
        "🎰 <b>SINAL DETECTADO – AVIATOR</b>\n\n"
        f"🕐 <b>Hora:</b> {sinal['hora']}\n"
        f"🎯 <b>Multiplicador:</b> <code>{sinal['multiplicador']}x</code>\n"
        f"📊 <b>Classificação:</b> {sinal['tipo']}\n"
        f"🔮 <b>Previsão:</b> {sinal['previsao']}\n\n"
        f"{sinal['mensagem'] or ''}\n\n"
        f"💰 Cadastre‑se com bônus:\n👉 <a href='{BANNER_LINK}'>{BANNER_LINK}</a>"
    )
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton("🔗 Cadastre‑se", url=BANNER_LINK)]]
    )
    try:
        for dest in (GRUPO_ID, CHAT_ID):
            await bot.send_photo(dest, photo=BANNER_IMG, caption=texto, reply_markup=markup)
        print(f"[SINAL] {sinal['multiplicador']}x às {sinal['hora']}")
    except Exception as exc:
        print("[ERRO ENVIO]", exc)


async def enviar_grafico() -> None:
    try:
        gerar_grafico(VELAS)
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton("🔗 Cadastre‑se", url=BANNER_LINK)]]
        )
        for dest in (GRUPO_ID, CHAT_ID):
            await bot.send_photo(
                dest,
                photo=FSInputFile(f"{STATIC_DIR}/chart.png"),
                caption="📈 <b>Histórico recente de acertos</b>",
                reply_markup=markup,
            )
        print("[GRÁFICO] enviado")
    except Exception as exc:
        print("[ERRO GRÁFICO]", exc)

# ╭────────────────────────── handlers telegram ─────────────────────────╮
@router.message(Command("start"))
async def h_start(m: Message) -> None:
    await m.answer("🚀 Bot Voo Milionário on‑line!\nUse /ajuda para comandos.")


@router.message(Command("grafico"))
async def h_grafico(m: Message) -> None:
    await enviar_grafico()


@router.message(Command("status"))
async def h_status(m: Message) -> None:
    await m.answer(
        f"📊 VELAS: {len(VELAS)}\n"
        f"🔄 Último mult: {ULTIMO_MULT}\n"
        f"💾 Último envio: {ULTIMO_ENVIO_ID}"
    )


@router.message(Command("ajuda"))
async def h_ajuda(m: Message) -> None:
    await m.answer(
        "ℹ️ <b>Comandos</b>\n"
        "/start   – Inicia o bot\n"
        "/grafico – Gráfico recente\n"
        "/sinais  – Últimos sinais\n"
        "/status  – Info rápidas\n"
        "/sobre   – Sobre o projeto"
    )


@router.message(Command("sinais"))
async def h_sinais(m: Message) -> None:
    path = f"{LOG_DIR}/sinais.jsonl"
    if not os.path.exists(path):
        await m.answer("Nenhum sinal registrado ainda."); return
    linhas = open(path, encoding="utf-8").read().strip().splitlines()[-5:]
    if not linhas:
        await m.answer("Nenhum sinal registrado ainda."); return
    itens = []
    for ln in linhas:
        d = json.loads(ln)
        itens.append(f"<b>{d['hora']}</b> — {d['multiplicador']}x ({d['tipo']})")
    await m.answer("📌 <b>Últimos sinais</b>:\n" + "\n".join(itens))


@router.message(Command("sobre"))
async def h_sobre(m: Message) -> None:
    await m.answer(
        "🤖 <b>Voo Milionário Bot</b> – Monitoramento 24/7 do Aviator "
        "e envio de sinais baseados em dados reais via WebSocket."
    )

# ╭────────────────────────── monitor loop WS ───────────────────────────╮
async def monitorar() -> None:  # noqa: C901  – função longa mas clara
    """Loop principal: consome coeficientes via WebSocket e decide quando enviar sinal."""
    global VELAS, ULTIMO_MULT
    while True:
        try:
            token = await get_token()
            url = WS_BASE_URL.format(token=token)
            print("[WS] Conectando ao Aviator…")
            async with websockets.connect(url, ping_interval=None) as ws:
                print("[WS] Conexão estabelecida.")
                async for msg in ws:
                    data = json.loads(msg)
                    if data.get("t") != "coefficient":
                        continue

                    coef = float(data["v"])
                    if coef == ULTIMO_MULT:
                        continue  # evita duplicados
                    ULTIMO_MULT = coef

                    VELAS.append(coef)
                    VELAS = VELAS[-20:]  # mantém histórico curto

                    hora = datetime.now(LUANDA_TZ).strftime("%H:%M:%S")
                    ts   = datetime.utcnow().isoformat()
                    prever, chance = prever_proxima_entrada(VELAS)

                    tipo = "🔥 Alta (≥ 1.99 x)" if coef >= VELA_MINIMA else "🢨 Baixa (< 1.99 x)"
                    msg  = None
                    if coef >= VELA_RARA:
                        tipo = "🚀 Rara (> 100 x)"
                        idx  = int(datetime.now().timestamp()) % len(MENSAGENS_MOTIVAS)
                        msg  = MENSAGENS_MOTIVAS[idx]

                    sinal = {
                        "hora": hora,
                        "multiplicador": coef,
                        "tipo": tipo,
                        "previsao": f"{chance}%" if prever else "Sem sinal",
                        "mensagem": msg,
                        "timestamp": ts,
                    }
                    salvar_log_sinal(sinal)
                    await enviar_sinal(sinal)
        except Exception as exc:
            print("[ERRO WS]", exc)
            print(f"[WS] Tentando reconectar em {RECONNECT_DELAY}s…")
            await asyncio.sleep(RECONNECT_DELAY)

# ──────────────────────────────────
# Registrar comandos
# ──────────────────────────────────
async def registrar_comandos() -> None:
    await bot.set_my_commands([
        BotCommand(command="start",   description="Iniciar"),
        BotCommand(command="grafico", description="Gráfico de acertos"),
        BotCommand(command="sinais",  description="Últimos sinais"),
        BotCommand(command="status",  description="Status"),
        BotCommand(command="ajuda",   description="Ajuda"),
        BotCommand(command="sobre",   description="Sobre o projeto"),
    ])
    print("[BOT] Comandos registrados")

# ╭───────────────────────────── startup ────────────────────────────────╮
async def iniciar_scraping() -> None:
    if not checar_instancia():
        return
    try:
        await registrar_comandos()
        asyncio.create_task(monitorar())
        await dp.start_polling(bot)
    finally:
        limpar_instancia()

# ╭────────────────────────── entry‑point  ──────────────────────────────╮
if __name__ == "__main__":
    asyncio.run(iniciar_scraping())

    # fake‑listener para Render (porta obrigatória)
    if os.getenv("RENDER"):
        port = int(os.getenv("PORT", 10000))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", port))
            s.listen()
            print(f"[RENDER] Escutando porta {port} (fake listener)")
            s.accept()
