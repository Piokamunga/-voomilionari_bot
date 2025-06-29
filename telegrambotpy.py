"""
telegrambotpy.py — Voo Milionário Bot
──────────────────────────────────────
Monitora o Aviator 24 h por dia e envia sinais no Telegram
sempre que o último multiplicador é ≥ 1 .99 x.

• Python ≥ 3.11   • aiogram 3.x
• aiohttp • pytz • matplotlib

Variáveis (.env) mínimas   ┄┄┄┄┄┄┄┄┄
TG_BOT_TOKEN   token do bot Telegram
CHAT_ID        ID do chat-admin (opcional)
GRUPO_ID       ID do grupo público (opcional)

Autor : Pio Ginga  (2025)
"""
# ============================================================
# IMPORTS
# ============================================================
from __future__ import annotations

import os
import re
import json
import socket
import asyncio
from datetime import datetime

import aiohttp
import pytz
import matplotlib.pyplot as plt
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

# ============================================================
# CONFIG. DE AMBIENTE
# ============================================================
load_dotenv()

TOKEN:    str | None = os.getenv("TG_BOT_TOKEN")
CHAT_ID:  str        = os.getenv("CHAT_ID",  "8101413562")
GRUPO_ID: str        = os.getenv("GRUPO_ID", "-1002769928832")

if not TOKEN:
    raise RuntimeError("Defina TG_BOT_TOKEN no .env!")

GAME_URL = (
    "https://m.goldenbet.ao/gameGo?"
    "id=1873916590817091585&code=2201&platform=PP"
)

# Limiares
VELA_MINIMA = 1.99      # envia sinal ≥ 1.99 x
VELA_RARA   = 100.0     # classifica como rara

# Fuso horário
LUANDA_TZ = pytz.timezone("Africa/Luanda")

# Links / mídia
BANNER_LINK = "https://bit.ly/449TH4F"
BANNER_IMG  = "https://i.ibb.co/ZcK9dcT/banner.png"

# Mensagens motivacionais
MENSAGENS_MOTIVAS = [
    "💥 Hoje pode ser o dia da sua virada!",
    "🎯 O sucesso está nos detalhes. Foco total!",
    "🚀 Quem voa alto não tem medo da queda!",
    "📈 Persistência transforma tentativas em vitórias!",
    "🎲 O próximo voo pode ser o milionário!",
]

# Persistência e cache
LOCK_FILE = ".bot_lock"
LOG_DIR   = "logs"
STATIC_DIR = "static"
os.makedirs(LOG_DIR,     exist_ok=True)
os.makedirs(STATIC_DIR,  exist_ok=True)

# ============================================================
# BOT & ROUTER
# ============================================================
bot     = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp      = Dispatcher()
router  = Router()
dp.include_router(router)

# Estado em memória
VELAS:           list[float] = []
ULTIMO_MULT:     float | None = None
ULTIMO_ENVIO_ID: str   | None = None

# ============================================================
# UTILITÁRIOS
# ============================================================
def checar_instancia() -> bool:
    """Garante instância única usando um arquivo de bloqueio."""
    if os.path.exists(LOCK_FILE):
        print("⚠️ Bot já está em execução.")
        return False
    with open(LOCK_FILE, "w") as f:
        f.write(datetime.utcnow().isoformat())
    return True


def limpar_instancia() -> None:
    os.remove(LOCK_FILE) if os.path.exists(LOCK_FILE) else None


def salvar_log_sinal(sinal: dict) -> None:
    """Registra sinal em arquivo .jsonl."""
    with open(f"{LOG_DIR}/sinais.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(sinal, ensure_ascii=False) + "\n")


# ----------  gráfico ----------
def gerar_grafico(seq: list[float]) -> None:
    acertos = [1 if v >= VELA_MINIMA else 0 for v in seq]
    plt.figure(figsize=(10, 3))
    plt.plot(acertos, marker="o", linewidth=1)
    plt.title("Acertos (≥ 1.99 x)")
    plt.grid(True, linestyle=":", linewidth=0.5)
    plt.tight_layout()
    plt.savefig(f"{STATIC_DIR}/chart.png")
    plt.close()


# ----------  parse ----------
VELA_REGEX = re.compile(r"(\d+(?:\.\d+)?)[xX]")


def extrair_velas(html: str) -> list[float]:
    """Extrai lista de multiplicadores do HTML da página."""
    return [float(m.group(1)) for m in VELA_REGEX.finditer(html)]


def prever_proxima_entrada(seq: list[float]) -> tuple[bool, float]:
    """Heurística simples para prever chance de subida."""
    if len(seq) < 2:
        return False, 0.0
    if seq[-1] < 2.0 and seq[-2] < 2.0:
        prob = 90 + round((2.0 - seq[-1])*5 + (2.0 - seq[-2])*5, 1)
        return True, min(prob, 99.9)
    return False, 0.0

# ============================================================
# HTTP – obtém página pública (não requer login)
# ============================================================
async def obter_html(session: aiohttp.ClientSession) -> str:
    try:
        async with session.get(GAME_URL, timeout=10) as resp:
            return await resp.text()
    except Exception as exc:
        print("[ERRO HTML]", exc)
        return ""

# ============================================================
# ENVIO DE MENSAGENS
# ============================================================
async def enviar_sinal(sinal: dict) -> None:
    global ULTIMO_ENVIO_ID
    msg_id = f"{sinal['timestamp']}-{sinal['multiplicador']}"
    if msg_id == ULTIMO_ENVIO_ID:
        return      # evita duplicidades
    ULTIMO_ENVIO_ID = msg_id

    texto = (
        "🎰 <b>SINAL DETECTADO – AVIATOR</b>\n\n"
        f"🕐 <b>Hora:</b> {sinal['hora']}\n"
        f"🎯 <b>Multiplicador:</b> <code>{sinal['multiplicador']}x</code>\n"
        f"📊 <b>Classificação:</b> {sinal['tipo']}\n"
        f"🔮 <b>Previsão:</b> {sinal['previsao']}\n\n"
        f"{sinal['mensagem'] or ''}\n\n"
        f"💰 Cadastre-se com bônus:\n👉 <a href='{BANNER_LINK}'>{BANNER_LINK}</a>"
    )

    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton("🔗 Cadastre-se", url=BANNER_LINK)]]
    )
    try:
        for dest in (GRUPO_ID, CHAT_ID):
            await bot.send_photo(dest, photo=BANNER_IMG, caption=texto, reply_markup=markup)
        print(f"[SINAL] {sinal['multiplicador']}x enviado às {sinal['hora']}")
    except Exception as exc:
        print("[ERRO ENVIO]", exc)


async def enviar_grafico() -> None:
    try:
        gerar_grafico(VELAS)
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton("🔗 Cadastre-se", url=BANNER_LINK)]]
        )
        for dest in (GRUPO_ID, CHAT_ID):
            await bot.send_photo(dest, FSInputFile(f"{STATIC_DIR}/chart.png"),
                                 caption="📈 <b>Últimos acertos</b>", reply_markup=markup)
        print("[GRÁFICO] enviado")
    except Exception as exc:
        print("[ERRO GRÁFICO]", exc)

# ============================================================
# HANDLERS ─ comandos Telegram
# ============================================================
@router.message(Command("start"))
async def cmd_start(m: Message) -> None:
    await m.answer(
        "🚀 Bot Voo Milionário on-line e monitorando o Aviator em tempo real!\n"
        "Use /grafico para ver o desempenho."
    )

@router.message(Command("grafico"))
async def cmd_grafico(m: Message) -> None:
    await enviar_grafico()

@router.message(Command("status"))
async def cmd_status(m: Message) -> None:
    await m.answer(
        f"📊 VELAS: {len(VELAS)}\n"
        f"🔄 Último mult: {ULTIMO_MULT}\n"
        f"💾 Último envio: {ULTIMO_ENVIO_ID}"
    )

@router.message(Command("ajuda"))
async def cmd_ajuda(m: Message) -> None:
    await m.answer(
        "ℹ️ <b>Comandos disponíveis</b>\n"
        "/start – Inicia o bot\n"
        "/ajuda – Esta ajuda\n"
        "/grafico – Gráfico recente\n"
        "/sinais – Últimos sinais\n"
        "/painel – Painel (em breve)\n"
        "/sobre – Sobre o projeto"
    )

@router.message(Command("sinais"))
async def cmd_sinais(m: Message) -> None:
    caminho = f"{LOG_DIR}/sinais.jsonl"
    if not os.path.exists(caminho):
        await m.answer("Nenhum sinal registrado ainda."); return
    linhas = open(caminho, encoding="utf-8").read().strip().splitlines()[-5:]
    if not linhas:
        await m.answer("Nenhum sinal registrado ainda."); return
    msgs = []
    for ln in linhas:
        d = json.loads(ln)
        msgs.append(f"<b>{d['hora']}</b> — {d['multiplicador']}x ({d['tipo']})")
    await m.answer("📌 <b>Últimos sinais</b>:\n" + "\n".join(msgs))

@router.message(Command("painel"))
async def cmd_painel(m: Message) -> None:
    await m.answer("📊 Painel em construção. Fique ligado!")

@router.message(Command("sobre"))
async def cmd_sobre(m: Message) -> None:
    await m.answer(
        "🤖 <b>Voo Milionário Bot</b> — Monitora o Aviator 24/7 e envia "
        "sinais baseados em multiplicadores reais. Uso educacional."
    )

# ============================================================
# LOOP PRINCIPAL
# ============================================================
async def monitorar() -> None:
    global VELAS, ULTIMO_MULT

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                html = await obter_html(session)
                if not html:
                    await asyncio.sleep(10); continue

                velas = extrair_velas(html)
                if not velas:
                    await asyncio.sleep(10); continue

                nova = velas[-1]
                if nova != ULTIMO_MULT:
                    VELAS.append(nova)
                    VELAS = VELAS[-20:]
                    ULTIMO_MULT = nova

                    hora = datetime.now(LUANDA_TZ).strftime("%H:%M:%S")
                    ts   = datetime.utcnow().isoformat()
                    prever, chance = prever_proxima_entrada(VELAS)

                    tipo = "🔥 Alta (≥ 1.99 x)" if nova >= VELA_MINIMA else "🢨 Baixa (< 1.99 x)"
                    msg  = None
                    if nova >= VELA_RARA:
                        tipo = "🚀 Rara (> 100 x)"
                        msg  = MENSAGENS_MOTIVAS[int(datetime.now().timestamp()) % len(MENSAGENS_MOTIVAS)]

                    sinal = {
                        "hora": hora,
                        "multiplicador": nova,
                        "tipo": tipo,
                        "previsao": f"{chance}%" if prever else "Sem sinal",
                        "mensagem": msg,
                        "timestamp": ts,
                    }
                    salvar_log_sinal(sinal)
                    await enviar_sinal(sinal)

                await asyncio.sleep(5)

            except Exception as exc:
                print("[ERRO MONITOR]", exc)
                await asyncio.sleep(10)

 ============================================================
# REGISTRO DE COMANDOS
# ============================================================
async def registrar_comandos() -> None:
    cmds = [
        ("start",  "Iniciar"),
        ("ajuda",  "Ajuda"),
        ("sinais", "Últimos sinais"),
        ("grafico","Gráfico"),
        ("painel", "Painel"),
        ("sobre",  "Sobre"),
    ]
    await bot.set_my_commands([BotCommand(c, d) for c, d in cmds]

# -------------------------
# ENTRY-POINT
# -------------------------
if __name__ == "__main__":
    asyncio.run(iniciar_scraping())

    # Listener “fake” para Render (free tier) — evita erro de porta
    if os.getenv("RENDER"):
        port = int(os.getenv("PORT", 10000))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", port))
            s.listen()
            print(f"[RENDER] Fake listener ativo na porta {port}")
            s.accept()
