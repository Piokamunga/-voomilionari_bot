"""
telegrambotpy.py – Voo Milionário Bot

Monitora o jogo Aviator 24/7 e envia sinais no Telegram quando identifica
multiplicadores iguais ou superiores a 1.99x.

Requisitos principais:

Python ≥ 3.11  
aiogram 3.x  
aiohttp, pytz, matplotlib  
selenium, webdriver-manager  
Chrome ou Chromium instalado (para Selenium headless)

Autor: Pio Ginga (2025)
"""

# ==========================
# IMPORTS
# ==========================

# Standard library
import os
import re
import json
import asyncio
import pathlib
from datetime import datetime, timedelta
from typing import List, Tuple

# Third‑party libraries
import aiohttp
import pytz
import matplotlib.pyplot as plt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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

# ==========================
# VARIÁVEIS DE AMBIENTE
# ==========================

load_dotenv()
TOKEN: str | None = os.getenv("TG_BOT_TOKEN")
CHAT_ID: str = os.getenv("CHAT_ID", "8101413562")
GRUPO_ID: str = os.getenv("GRUPO_ID", "-1002769928832")
USERNAME: str | None = os.getenv("GB_USERNAME")
PASSWORD: str | None = os.getenv("GB_PASSWORD")

if not all([TOKEN, USERNAME, PASSWORD]):
    raise RuntimeError("As variáveis TG_BOT_TOKEN, GB_USERNAME e GB_PASSWORD devem estar definidas no .env")

LOGIN_URL = "https://m.goldenbet.ao/index/login"
GAME_URL = "https://m.goldenbet.ao/gameGo?id=1873916590817091585&code=2201&platform=PP"

VELA_MINIMA = 1.99
VELA_RARA = 100.0
LUANDA_TZ = pytz.timezone("Africa/Luanda")

BANNER_LINK = "https://bit.ly/449TH4F"
BANNER_IMAGEM = "https://i.ibb.co/ZcK9dcT/banner.png"

COOKIE_FILE = "cookies_gb.json"
LOCK_FILE = ".bot_lock"
LOG_DIR = "logs"
STATIC_DIR = "static"

for pasta in (LOG_DIR, STATIC_DIR):
    os.makedirs(pasta, exist_ok=True)

MENSAGENS_MOTIVAS: List[str] = [
    "💥 Hoje pode ser o dia da sua virada!",
    "🎯 O sucesso está nos detalhes. Foco total!",
    "🚀 Quem voa alto não tem medo da queda!",
    "📈 Persistência transforma tentativas em vitórias!",
    "🎲 O próximo voo pode ser o milionário!",
]

# ==========================
# INSTÂNCIAS DO BOT
# ==========================

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

VELAS: List[float] = []
ULTIMO_MULT: float | None = None
ULTIMO_ENVIO_ID: str | None = None

# ==========================
# FUNÇÕES AUXILIARES
# ==========================

def checar_instancia() -> bool:
    if pathlib.Path(LOCK_FILE).exists():
        print("⚠️ Bot já está em execução.")
        return False
    pathlib.Path(LOCK_FILE).write_text(datetime.utcnow().isoformat())
    return True

def limpar_instancia() -> None:
    pathlib.Path(LOCK_FILE).unlink(missing_ok=True)

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

VELA_REGEX = re.compile(r"(\d+(?:\.\d+)?)[xX]")

def extrair_velas(html: str) -> List[float]:
    return [float(m.group(1)) for m in VELA_REGEX.finditer(html)]

def prever_proxima_entrada(ultimas: List[float]) -> Tuple[bool, float]:
    if len(ultimas) < 2:
        return False, 0.0
    if ultimas[-1] < 2.0 and ultimas[-2] < 2.0:
        chance = 90 + round((2.0 - ultimas[-1]) * 5 + (2.0 - ultimas[-2]) * 5, 1)
        return True, min(chance, 99.9)
    return False, 0.0

# ==========================
# LOGIN HEADLESS (SELENIUM)
# ==========================

def obter_cookies_selenium() -> dict:
    if pathlib.Path(COOKIE_FILE).exists():
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(LOGIN_URL)
    driver.implicitly_wait(5)

    driver.find_element(By.NAME, "account").send_keys(USERNAME)
    driver.find_element(By.NAME, "password").send_keys(PASSWORD + Keys.RETURN)
    driver.implicitly_wait(5)

    if "login" in driver.current_url.lower():
        driver.quit()
        raise RuntimeError("Falha no login via Selenium.")

    cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
    driver.quit()

    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f)

    return cookies

GB_COOKIES = obter_cookies_selenium()

# ==========================
# REQUISIÇÕES HTTP
# ==========================

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
                print("[HTML] Sessão expirada – realizando novo login…")
                if await login(session):
                    return await obter_html(session)
                return ""
            print("[HTML] len:", len(html))
            return html
    except Exception as exc:
        print("[ERRO HTML]", exc)
        return ""

# ==========================
# ENVIO DE SINAL & GRÁFICO
# ==========================

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
        for destino in (GRUPO_ID, CHAT_ID):
            await bot.send_photo(destino, photo=BANNER_IMAGEM, caption=texto, reply_markup=markup)
        print(f"[SINAL] Enviado: {sinal['multiplicador']}x às {sinal['hora']}")
    except Exception as exc:
        print("[ERRO ENVIO]", exc)

async def enviar_grafico() -> None:
    try:
        gerar_grafico(VELAS)
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔗 Cadastre-se", url=BANNER_LINK)]]
        )
        for destino in (GRUPO_ID, CHAT_ID):
            await bot.send_photo(
                destino,
                photo=FSInputFile(f"{STATIC_DIR}/chart.png"),
                caption="📈 <b>Últimos acertos registrados</b>",
                reply_markup=markup,
            )
        print("[GRÁFICO] Enviado com sucesso")
    except Exception as exc:
        print("[ERRO GRÁFICO]", exc)

# ==========================
# HANDLERS TELEGRAM
# ==========================

@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    await message.answer(
        "🚀 Bot Voo Milionário está online e monitorando o Aviator em tempo real!\nUse /grafico para ver o desempenho."
    )

@router.message(Command("grafico"))
async def grafico_handler(message: Message) -> None:
    await enviar_grafico()

@router.message(Command("status"))
async def status_handler(message: Message) -> None:
    texto = (
        f"📊 VELAS armazenadas: {len(VELAS)}\n"
        f"🔄 Último mult: {ULTIMO_MULT}\n"
        f"💾 Último envio: {ULTIMO_ENVIO_ID}"
    )
    await message.answer(texto)

@router.message(Command("ajuda"))
async def ajuda_handler(message: Message) -> None:
    texto = (
        "ℹ️ <b>Comandos disponíveis</b>\n"
        "/start  — Inicia o bot\n"
        "/ajuda  — Mostra esta ajuda\n"
        "/grafico — Último gráfico de acertos\n"
        "/sinais  — Lista dos últimos sinais\n"
        "/painel  — Painel de status (em breve)\n"
        "/sobre   — Sobre este projeto"
    )
    await message.answer(texto)

@router.message(Command("sinais"))
async def sinais_handler(message: Message) -> None:
    caminho = pathlib.Path(f"{LOG_DIR}/sinais.jsonl")
    if not caminho.exists():
        await message.answer("Nenhum sinal registrado ainda.")
        return

    try:
        linhas = caminho.read_text(encoding="utf-8").strip().splitlines()[-5:]
        if not linhas:
            await message.answer("Nenhum sinal registrado ainda.")
            return

        mensagens = []
        for linha in linhas:
            dado = json.loads(linha)
            mensagens.append(
                f"<b>{dado['hora']}</b> — {dado['multiplicador']}x ({dado['tipo']})"
            )
        await message.answer("📌 <b>Últimos sinais</b>:\n" + "\n".join(mensagens))
    except Exception as exc:
        await message.answer("Erro ao buscar sinais.")
        print("[ERRO SINAIS]", exc)

@router.message(Command("painel"))
async def painel_handler(message: Message) -> None:
    await message.answer("📊 Painel em construção. Fique ligado para novidades!")

@router.message(Command("sobre"))
async def sobre_handler(message: Message) -> None:
    await message.answer(
        "🤖 <b>Voo Milionário Bot</b> — Monitora o jogo Aviator 24/7 e envia sinais baseados em multiplicadores reais. Desenvolvido para fins educacionais."
    )

# ==========================
# LOOP DE MONITORAMENTO
# ==========================

async def monitorar() -> None:
    global VELAS, ULTIMO_MULT

    async with aiohttp.ClientSession(cookies=GB_COOKIES) as session:
        while True:
            try:
                html = await obter_html(session)
                if not html:
                    await asyncio.sleep(10)
                    continue

                velas_atual = extrair_velas(html)
                if not velas_atual:
                    await asyncio.sleep(10)
                    continue

                nova = velas_atual[-1]
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
                        mensagem = MENSAGENS_MOTIVAS[int(datetime.now().timestamp()) % len(MENSAGENS_MOTIVAS)]

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
                print("[ERRO LOOP MONITORAMENTO]", exc)
                await asyncio.sleep(10)

# ==========================
# REGISTRAR COMANDOS
# ==========================

async def registrar_comandos() -> None:
    comandos = [
        ("start", "Iniciar o bot"),
        ("ajuda", "Ver comandos"),
        ("sinais", "Últimos sinais"),
        ("grafico", "Gráfico de acertos"),
        ("painel", "Painel (em construção)"),
        ("sobre", "Sobre o projeto"),
    ]
    await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in comandos])
    print("[BOT] Comandos registrados!")

# ==========================
# INICIALIZAÇÃO
# ==========================

async def iniciar_scraping() -> None:
    if not checar_instancia():
        return
    try:
        await registrar_comandos()
        asyncio.create_task(monitorar())
        await dp.start_polling(bot)
    finally:
        limpar_instancia()

if __name__ == "__main__":
    asyncio.run(iniciar_scraping())
