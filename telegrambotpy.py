"""
telegrambotpy.py — Voo Milionário Bot (modular)
────────────────────────────────────────────────
Funções:
• Envia sinais no Telegram via função `enviar_sinal(valor)`
• Fornece comandos interativos no Telegram (/start, /grafico etc.)
• Roda 24/7 como parte do sistema orquestrado por main.py

Usado por:
• save_html_loop.py (regex HTML)
• save_html_loop_ws.py (WebSocket tempo real)

Variáveis (.env):
─────────────────
TG_BOT_TOKEN   token do bot
CHAT_ID        id do grupo/canal ou usuário
GRUPO_ID       grupo público (opcional)
"""

import os
import json
import asyncio
from datetime import datetime

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

import matplotlib.pyplot as plt
import pytz

# ╭─────────────────────────── Configurações ───────────────────────────╮

TOKEN     = os.getenv("TG_BOT_TOKEN")
CHAT_ID   = os.getenv("CHAT_ID", "8101413562")
GRUPO_ID  = os.getenv("GRUPO_ID", "-1002769928832")

VELA_MINIMA = 1.99
VELA_RARA   = 100.0
LUANDA_TZ   = pytz.timezone("Africa/Luanda")
LOG_DIR     = "logs"
STATIC_DIR  = "static"

BANNER_LINK = "https://bit.ly/449TH4F"
BANNER_IMG  = "https://i.ibb.co/ZcK9dcT/banner.png"
MENSAGENS_MOTIVAS = [
    "💥 Hoje pode ser o dia da sua virada!",
    "🎯 O sucesso está nos detalhes. Foco total!",
    "🚀 Quem voa alto não tem medo da queda!",
    "📈 Persistência transforma tentativas em vitórias!",
    "🎲 O próximo voo pode ser o milionário!",
]

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# ╭─────────────────────────── Bot e Dispatcher ─────────────────────────╮

bot    = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp     = Dispatcher()
router = Router()
dp.include_router(router)

VELAS: list[float] = []
ULTIMO_ENVIO_ID: str | None = None

# ╭────────────────────── Utilitários do Bot ───────────────────────────╮

def salvar_log_sinal(sinal: dict):
    with open(f"{LOG_DIR}/sinais.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(sinal, ensure_ascii=False) + "\n")

def gerar_grafico(seq: list[float]):
    acertos = [1 if v >= VELA_MINIMA else 0 for v in seq]
    plt.figure(figsize=(10, 3))
    plt.plot(acertos, marker="o", linewidth=1)
    plt.title("Acertos (≥ 1.99 x)")
    plt.grid(True, linestyle=":", linewidth=0.5)
    plt.tight_layout()
    plt.savefig(f"{STATIC_DIR}/chart.png")
    plt.close()

# ╭────────────────────── Função principal externa ─────────────────────╮

async def enviar_sinal(valor: float):
    """Pode ser chamada externamente pelos scrapers."""
    global ULTIMO_ENVIO_ID

    ts = datetime.utcnow().isoformat()
    hora = datetime.now(LUANDA_TZ).strftime("%H:%M:%S")
    msg_id = f"{ts}-{valor}"

    if msg_id == ULTIMO_ENVIO_ID:
        return
    ULTIMO_ENVIO_ID = msg_id

    tipo = "🔥 Alta (≥ 1.99 x)" if valor >= VELA_MINIMA else "🢨 Baixa (< 1.99 x)"
    msg = None
    if valor >= VELA_RARA:
        tipo = "🚀 Rara (> 100 x)"
        idx = int(datetime.now().timestamp()) % len(MENSAGENS_MOTIVAS)
        msg = MENSAGENS_MOTIVAS[idx]

    sinal = {
        "hora": hora,
        "multiplicador": valor,
        "tipo": tipo,
        "previsao": "–",
        "mensagem": msg,
        "timestamp": ts,
    }

    salvar_log_sinal(sinal)

    texto = (
        "🎰 <b>SINAL DETECTADO – AVIATOR</b>\n\n"
        f"🕐 <b>Hora:</b> {hora}\n"
        f"🎯 <b>Multiplicador:</b> <code>{valor:.2f}x</code>\n"
        f"📊 <b>Classificação:</b> {tipo}\n"
        f"{msg or ''}\n\n"
        f"💰 Cadastre‑se com bônus:\n👉 <a href='{BANNER_LINK}'>{BANNER_LINK}</a>"
    )

    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton("🔗 Cadastre‑se", url=BANNER_LINK)]]
    )

    for dest in (GRUPO_ID, CHAT_ID):
        try:
            await bot.send_photo(dest, photo=BANNER_IMG, caption=texto, reply_markup=markup)
        except Exception as exc:
            print("[ERRO ENVIO]", exc)

    print(f"[BOT] Sinal enviado: {valor:.2f}x")

# ╭────────────────────────── Handlers Telegram ────────────────────────╮

@router.message(Command("start"))
async def h_start(m: Message):
    await m.answer("🚀 Bot Voo Milionário on‑line!\nUse /ajuda para comandos.")

@router.message(Command("grafico"))
async def h_grafico(m: Message):
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

@router.message(Command("sinais"))
async def h_sinais(m: Message):
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

@router.message(Command("ajuda"))
async def h_ajuda(m: Message):
    await m.answer(
        "ℹ️ <b>Comandos</b>\n"
        "/start   – Inicia o bot\n"
        "/grafico – Gráfico recente\n"
        "/sinais  – Últimos sinais\n"
    )

# ╭────────────────────────── Inicialização bot ────────────────────────╮

async def iniciar_bot():
    await bot.set_my_commands([
        BotCommand(command="start", description="Iniciar"),
        BotCommand(command="grafico", description="Gráfico de acertos"),
        BotCommand(command="sinais", description="Últimos sinais"),
        BotCommand(command="ajuda", description="Ajuda"),
    ])
    print("[BOT] Iniciando polling…")
    await dp.start_polling(bot)
