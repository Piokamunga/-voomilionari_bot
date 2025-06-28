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
# VARIÁVEIS DE AMBIENTE
# ============================================================
load_dotenv()
TOKEN    = os.getenv("TG_BOT_TOKEN")
CHAT_ID  = os.getenv("CHAT_ID")  or "8101413562"
GRUPO_ID = os.getenv("GRUPO_ID") or "-1002769928832"
USERNAME = os.getenv("GB_USERNAME")
PASSWORD = os.getenv("GB_PASSWORD")

LOGIN_URL = "https://m.goldenbet.ao/index/login"
GAME_URL  = "https://m.goldenbet.ao/gameGo?id=1873916590817091585&code=2201&platform=PP"

VELA_MINIMA, VELA_RARA = 1.99, 100.0
LUANDA_TZ               = pytz.timezone("Africa/Luanda")

banner_link   = "https://bit.ly/449TH4F"
banner_imagem = "https://i.ibb.co/ZcK9dcT/banner.png"

MENSAGENS_MOTIVAS = [
    "💥 Hoje pode ser o dia da sua virada!",
    "🎯 O sucesso está nos detalhes. Foco total!",
    "🚀 Quem voa alto não tem medo da queda!",
    "📈 Persistência transforma tentativas em vitórias!",
    "🎲 O próximo voo pode ser o milionário!",
]

LOCK_FILE, LOG_DIR = ".bot_lock", "logs"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

# ============================================================
# INSTÂNCIAS DO BOT
# ============================================================
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()
router = Router()
dp.include_router(router)

VELAS: list[float] = []
ULTIMO_MULT: float | None = None
ULTIMO_ENVIO_ID: str | None = None

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def checar_instancia() -> bool:
    if os.path.exists(LOCK_FILE):
        print("⚠️ Bot já está em execução.")
        return False
    with open(LOCK_FILE, "w") as f:
        f.write(str(datetime.utcnow()))
    return True

def limpar_instancia():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

def salvar_log_sinal(sinal: dict):
    with open(f"{LOG_DIR}/sinais.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(sinal, ensure_ascii=False) + "\n")

def gerar_grafico(velas):
    acertos = [1 if v >= VELA_MINIMA else 0 for v in velas]
    plt.figure(figsize=(10, 3))
    plt.plot(acertos, marker="o", linewidth=1)
    plt.title("Acertos (≥1.99x)")
    plt.grid(True, linestyle=":", linewidth=0.5)
    plt.tight_layout()
    plt.savefig("static/chart.png")
    plt.close()

VELA_REGEX = re.compile(r"(\d+(?:\.\d+)?)[xX]")

def extrair_velas(html: str):
    return [float(m.group(1)) for m in VELA_REGEX.finditer(html)]

def prever_proxima_entrada(ultimas):
    if len(ultimas) < 2:
        return False, 0
    if ultimas[-1] < 2.0 and ultimas[-2] < 2.0:
        chance = 90 + round((2.0 - ultimas[-1]) * 5 + (2.0 - ultimas[-2]) * 5, 1)
        return True, min(chance, 99.9)
    return False, 0

# ============================================================
# REQUISIÇÕES HTTP
# ============================================================
async def login(session: aiohttp.ClientSession):
    try:
        payload = {"account": USERNAME, "password": PASSWORD}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with session.post(LOGIN_URL, data=payload, headers=headers) as resp:
            return resp.status == 200
    except Exception as e:
        print("[LOGIN EXCEPTION]", e)
        return False

async def obter_html(session: aiohttp.ClientSession):
    if not await login(session):
        return ""
    try:
        async with session.get(GAME_URL, timeout=10) as resp:
            html = await resp.text()
            return html if "login" not in html.lower() else ""
    except Exception as e:
        print("[ERRO HTML]", e)
        return ""

# ============================================================
# ENVIO DE SINAL E GRÁFICO
# ============================================================
async def enviar_sinal(sinal: dict):
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
        f"💰 Cadastre-se com bônus:\n👉 <a href='{banner_link}'>{banner_link}</a>"
    )

    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("🔗 Cadastre-se", url=banner_link)]])
    try:
        await bot.send_photo(GRUPO_ID, banner_imagem, caption=texto, reply_markup=markup)
        await bot.send_photo(CHAT_ID,  banner_imagem, caption=texto, reply_markup=markup)
    except Exception as e:
        print("[ERRO ENVIO]", e)

async def enviar_grafico():
    try:
        gerar_grafico(VELAS)
        markup = InlineKeyboardMarkup( inline_keyboard=[[InlineKeyboardButton("🔗 Cadastre-se", url=banner_link)]] )
        for cid in (GRUPO_ID, CHAT_ID):
            await bot.send_photo(cid, FSInputFile("static/chart.png"), caption="📈 <b>Últimos acertos registrados</b>", reply_markup=markup)
    except Exception as e:
        print("[ERRO GRÁFICO]", e)

# ============================================================
# HANDLERS
# ============================================================
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🚀 Bot Voo Milionário online e monitorando o Aviator em tempo real! Use /ajuda para ver comandos.")

@router.message(Command("grafico"))
async def cmd_grafico(message: Message):
    await enviar_grafico()

@router.message(Command("status"))
async def cmd_status(message: Message):
    await message.answer(f"📊 Velas: {len(VELAS)} | Último mult: {ULTIMO_MULT} | Último envio: {ULTIMO_ENVIO_ID}")

@router.message(Command("ajuda"))
async def cmd_ajuda(message: Message):
    await message.answer(
        "ℹ️ <b>Comandos disponíveis</b>\n"
        "/start — Inicia o bot\n"
        "/ajuda — Mostra esta ajuda\n"
        "/grafico — Último gráfico de acertos\n"
        "/sinais — Últimos sinais registrados\n"
        "/painel — Painel (em breve)\n"
        "/sobre — Sobre este projeto"
    )

@router.message(Command("sinais"))
async def cmd_sinais(message: Message):
    try:
        path = f"{LOG_DIR}/sinais.jsonl"
        if not os.path.exists(path):
            await message.answer("Nenhum sinal registrado ainda.")
            return

        with open(path, "r", encoding="utf-8") as f:
            linhas = f.readlines()[-5:]

        if not linhas:
            await message.answer("Nenhum sinal registrado ainda.")
            return

        mensagens = []
        for linha in linhas:
            dado = json.loads(linha)
            mensagens.append(f"<b>{dado['hora']}</b> — {dado['multiplicador']}x ({dado['tipo']})")

        resposta = "📌 <b>Últimos sinais</b>:
" + "
".join(mensagens)
        await message.answer(resposta)

    except Exception as e:
        print("[ERRO SINAIS]", e)
        await message.answer("Erro ao buscar sinais.")
            await message.answer("Nenhum sinal registrado ainda.")
            return
        mensagens = []
        for linha in linhas:
            dado = json.loads(linha)
            mensagens.append(f"<b>{dado['hora']}</b> — {dado['multiplicador']}x ({dado['tipo']})")
        await message.answer("📌 <b>Últimos sinais</b>:
" + "
".join(mensagens)))
    except Exception as e:
        print("[ERRO SINAIS]", e)
        await message.answer("Erro ao buscar sinais.")

@router.message(Command("painel"))
async def cmd_painel(message: Message):
    await message.answer("📊 Painel em construção. Fique ligado para novidades!")

@router.message(Command("sobre"))
async def cmd_sobre(message: Message):
    await message.answer("🤖 <b>Voo Milionário Bot</b> — Monitora o jogo Aviator 24/7 e envia sinais baseados em multiplicadores reais. Desenvolvido para fins educacionais.")

# ============================================================
# LOOP MONITORAMENTO
# ============================================================
async def monitorar():
    global VELAS, ULTIMO_MULT
    async with aiohttp.ClientSession() as session:
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
                    if len(VELAS) > 20:
                        VELAS.pop(0)
                    ULTIMO_MULT = nova
                    hora = datetime.now(LUANDA_TZ).strftime("%H:%M:%S")
                    timestamp = datetime.utcnow().isoformat()
                    prever, chance = prever_proxima_entrada(VELAS)
                    tipo = "🔥 Alta (≥1.99x)" if nova >= VELA_MINIMA else "🢨 Baixa (<1.99x)"
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
            except Exception as e:
                print("[ERRO MONITORAMENTO]", e)
                await asyncio.sleep(10)

# ============================================================
# REGISTRAR COMANDOS
# ============================================================
async def registrar_comandos():
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

# ============================================================
# INICIALIZAÇÃO
# ============================================================
async def iniciar_scraping():
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
