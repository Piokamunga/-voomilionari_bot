from __future__ import annotations

# ╭─────────────────────────────── imports ──────────────────────────────╮
import asyncio
import json
import os
import re
from datetime import datetime

import aiohttp
import matplotlib.pyplot as plt
import pytz
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
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

# ╭────────────────────── configuração de ambiente ──────────────────────╮
load_dotenv()

TOKEN: str | None = os.getenv("TG_BOT_TOKEN")
CHAT_ID: str = os.getenv("CHAT_ID", "8101413562")
GRUPO_ID: str = os.getenv("GRUPO_ID", "-1002769928832")
DEBUG: bool = os.getenv("DEBUG", "0") == "1"

if not TOKEN:
    raise RuntimeError("Defina TG_BOT_TOKEN no .env!")

GAME_URL = (
    "https://m.goldenbet.ao/gameGo"
    "?id=1873916590817091585&code=2201&platform=PP"
)

VELA_MINIMA = 1.99
VELA_RARA   = 100.0
LUANDA_TZ   = pytz.timezone("Africa/Luanda")

BANNER_LINK = "https://bit.ly/449TH4F"
BANNER_IMG  = "https://i.ibb.co/ZcK9dcT/banner.png"

MENSAGENS_MOTIVAS: list[str] = [
    "\ud83d\udca5 Hoje pode ser o dia da sua virada!",
    "\ud83c\udfaf O sucesso est\u00e1 nos detalhes. Foco total!",
    "\ud83d\ude80 Quem voa alto n\u00e3o tem medo da queda!",
    "\ud83d\udcc8 Persist\u00eancia transforma tentativas em vit\u00f3rias!",
    "\ud83c\udfb2 O pr\u00f3ximo voo pode ser o milion\u00e1rio!",
]

LOCK_FILE   = ".bot_lock"
LOG_DIR     = "logs"
STATIC_DIR  = "static"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# ╭─────────────────────────── bot & router ─────────────────────────────╮
bot    = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp     = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# estado em memória
VELAS: list[float]        = []
ULTIMO_MULT: float | None = None
ULTIMO_ENVIO_ID: str | None = None

# ╭───────────────────────────── utils ──────────────────────────────────╮
def checar_instancia() -> bool:
    if os.path.exists(LOCK_FILE):
        print("\u26a0\ufe0f  Bot j\u00e1 est\u00e1 em execu\u00e7\u00e3o.")
        return False
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(datetime.utcnow().isoformat())
    return True

def limpar_instancia() -> None:
    os.remove(LOCK_FILE) if os.path.exists(LOCK_FILE) else None

def salvar_log_sinal(sinal: dict) -> None:
    with open(f"{LOG_DIR}/sinais.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(sinal, ensure_ascii=False) + "\n")

def gerar_grafico(seq: list[float]) -> None:
    acertos = [1 if v >= VELA_MINIMA else 0 for v in seq]
    plt.figure(figsize=(10, 3))
    plt.plot(acertos, marker="o", linewidth=1)
    plt.title("Acertos (\u2265 1.99 x)")
    plt.grid(True, linestyle=":", linewidth=0.5)
    plt.tight_layout()
    plt.savefig(f"{STATIC_DIR}/chart.png")
    plt.close()

# ╭─────────────────────────── HTTP helpers ─────────────────────────────╮
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

CANDIDATE_REGEXES: dict[str, str] = {
    r"(\d+(?:[.,]\d+)?)[xX]\b": "número + x   (ex.: 2.31x)",
    r'"multiplier"\s*:\s*"?(\d+(?:[.,]\d+)?)': 'JSON "multiplier": "2.31"',
    r'data-value\s*=\s*"(\d+(?:[.,]\d+)?)"': 'data-value="2.31"',
}
VELA_REGEX: re.Pattern | None = None

async def detectar_melhor_regex(session: aiohttp.ClientSession) -> None:
    global VELA_REGEX
    tot = {pat: 0 for pat in CANDIDATE_REGEXES}
    for _ in range(3):
        try:
            async with session.get(GAME_URL, headers=HEADERS, timeout=10) as r:
                html = await r.text()
        except Exception as exc:
            print("[ERRO HTML start]", exc)
            continue
        for pat in tot:
            tot[pat] += len(re.findall(pat, html, flags=re.I))
        await asyncio.sleep(1)
    melhor, qtd = max(tot.items(), key=lambda kv: kv[1])
    if qtd == 0:
        print("\u26a0\ufe0f  Nenhum pattern encontrou multiplicadores")
        VELA_REGEX = re.compile(r"$^")
    else:
        VELA_REGEX = re.compile(melhor, flags=re.I)
        desc = CANDIDATE_REGEXES[melhor]
        print(f"[AUTO-REGEX] Selecionado: {desc}  (total {qtd}/3)")

async def obter_html(session: aiohttp.ClientSession) -> str:
    try:
        async with session.get(GAME_URL, headers=HEADERS, timeout=10) as r:
            html = await r.text()
            if DEBUG:
                print("[DEBUG] HTML len:", len(html))
            return html
    except Exception as exc:
        print("[ERRO HTML]", exc)
        return ""

# ╭────────────────────── parsing & previsão ────────────────────────────╮
def extrair_velas(html: str) -> list[float]:
    if VELA_REGEX is None:
        return []
    return [float(v.replace(",", ".")) for v in VELA_REGEX.findall(html)]

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
        "\ud83c\udfb0 <b>SINAL DETECTADO – AVIATOR</b>\n\n"
        f"\ud83d\udd50 <b>Hora:</b> {sinal['hora']}\n"
        f"\ud83c\udfaf <b>Multiplicador:</b> <code>{sinal['multiplicador']}x</code>\n"
        f"\ud83d\udcca <b>Classificação:</b> {sinal['tipo']}\n"
        f"\ud83d\udd2e <b>Previsão:</b> {sinal['previsao']}\n\n"
        f"{sinal['mensagem'] or ''}\n\n"
        f"\ud83d\udcb0 Cadastre-se com bônus:\n\ud83d\udc49 <a href='{BANNER_LINK}'>{BANNER_LINK}</a>"
    )
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton("\ud83d\udd17 Cadastre-se", url=BANNER_LINK)]]
    )
    try:
        for dest in (GRUPO_ID, CHAT_ID):
            await bot.send_photo(dest, photo=BANNER_IMG, caption=texto, reply_markup=markup)
        print(f"[SINAL] {sinal['multiplicador']}x \u00e0s {sinal['hora']}")
    except Exception as exc:
        print("[ERRO ENVIO]", exc)

async def enviar_grafico() -> None:
    try:
        gerar_grafico(VELAS)
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton("\ud83d\udd17 Cadastre-se", url=BANNER_LINK)]]
        )
        for dest in (GRUPO_ID, CHAT_ID):
            await bot.send_photo(
                dest,
                photo=FSInputFile(f"{STATIC_DIR}/chart.png"),
                caption="\ud83d\udcc8 <b>Histórico recente de acertos</b>",
                reply_markup=markup,
            )
        print("[GRÁFICO] enviado")
    except Exception as exc:
        print("[ERRO GRÁFICO]", exc)

# ╭────────────────────────── handlers telegram ─────────────────────────╮
@router.message(Command("start"))
async def h_start(m: Message) -> None:
    await m.answer("\ud83d\ude80 Bot Voo Milionário on-line!\nUse /ajuda para comandos.")

@router.message(Command("grafico"))
async def h_grafico(m: Message) -> None:
    await enviar_grafico()

@router.message(Command("status"))
async def h_status(m: Message) -> None:
    await m.answer(
        f"\ud83d\udcca VELAS: {len(VELAS)}\n"
        f"\ud83d\udd04 Último mult: {ULTIMO_MULT}\n"
        f"\ud83d\udcc0 Último envio: {ULTIMO_ENVIO_ID}"
    )

@router.message(Command("ajuda"))
async def h_ajuda(m: Message) -> None:
    await m.answer(
        "\u2139\ufe0f <b>Comandos</b>\n"
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
    await m.answer("\ud83d\udccc <b>Últimos sinais</b>:\n" + "\n".join(itens))

@router.message(Command("sobre"))
async def h_sobre(m: Message) -> None:
    await m.answer(
        "\ud83e\udd16 <b>Voo Milionário Bot</b> – Monitoramento 24/7 do Aviator "
        "e envio de sinais baseados em dados reais."
    )

# ╭──────────────────────────── monitor loop ────────────────────────────╮
async def monitorar() -> None:
    global VELAS, ULTIMO_MULT
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                html = await obter_html(session)
                if not html:
                    await asyncio.sleep(10); continue
                velas = extrair_velas(html)
                if DEBUG:
                    print("[DEBUG] Velas extraídas:", velas[-10:])
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
                    tipo = "\ud83d\udd25 Alta (≥ 1.99 x)" if nova >= VELA_MINIMA else "\ud83d\udd28 Baixa (< 1.99 x)"
                    msg  = None
                    if nova >= VELA_RARA:
                        tipo = "\ud83d\ude80 Rara (> 100 x)"
                        idx  = int(datetime.now().timestamp()) % len(MENSAGENS_MOTIVAS)
                        msg  = MENSAGENS_MOTIVAS[idx]
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

# ╭────────────────────────── entry-point  ──────────────────────────────╮
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://voomilionari-bot.onrender.com{WEBHOOK_PATH}"

async def on_startup(app):
    if not checar_instancia():
        print("Instância já em execução.")
        raise RuntimeError("Instância duplicada")
    await registrar_comandos()
    async with aiohttp.ClientSession() as sess:
        await detectar_melhor_regex(sess)
    asyncio.create_task(monitorar())
    await bot.set_webhook(WEBHOOK_URL)
    print("[WEBHOOK] Registrado com sucesso")

async def on_shutdown(app):
    await bot.delete_webhook()
    limpar_instancia()
    print("[WEBHOOK] Removido com sucesso")

async def main():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp)

    port = int(os.getenv("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    asyncio.run(main())
