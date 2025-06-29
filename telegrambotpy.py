"""
telegrambotpy.py — Voo Milionário Bot
Monitora Aviator 24/7, envia sinais ≥1.99 x e gráfico automático.
Autor: Pio Ginga • 2025
"""

# =============== IMPORTS ===============
import os, re, json, socket, asyncio, aiohttp, pytz, matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import List, Tuple
from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
                           FSInputFile, BotCommand)
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
# ======================================

# ----------- .env variáveis -----------
load_dotenv()
TOKEN      = os.getenv("TG_BOT_TOKEN")
CHAT_ID    = os.getenv("CHAT_ID", "8101413562")
GRUPO_ID   = os.getenv("GRUPO_ID", "-1002769928832")

if not TOKEN:
    raise RuntimeError("Defina TG_BOT_TOKEN no .env")

GAME_URL = ("https://m.goldenbet.ao/gameGo?"
            "id=1873916590817091585&code=2201&platform=PP")

VELA_MINIMA = 1.99
VELA_RARA   = 100.0
LUANDA_TZ   = pytz.timezone("Africa/Luanda")

BANNER_LINK, BANNER_IMAGEM = (
    "https://bit.ly/449TH4F",
    "https://i.ibb.co/ZcK9dcT/banner.png",
)

LOCK_FILE, LOG_DIR, STATIC_DIR = ".bot_lock", "logs", "static"
for pasta in (LOG_DIR, STATIC_DIR):
    os.makedirs(pasta, exist_ok=True)

MENSAGENS_MOTIVAS = [
    "💥 Hoje pode ser o dia da sua virada!",
    "🎯 O sucesso está nos detalhes. Foco total!",
    "🚀 Quem voa alto não tem medo da queda!",
    "📈 Persistência transforma tentativas em vitórias!",
    "🎲 O próximo voo pode ser o milionário!",
]

# ---- Bot instância & estado ----------
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp, router = Dispatcher(), Router()
dp.include_router(router)

VELAS: List[float] = []
ULTIMO_MULT: float | None = None
ULTIMO_ENVIO_ID: str   | None = None

GRAPH_INTERVAL_SEC = 300            # 300 s (5 min) — mude p/ ≥ 60 s se quiser
ULTIMO_GRAFICO: datetime | None = None
# ======================================

# ============ FUNÇÕES AUX =============
def checar_instancia() -> bool:
    if os.path.exists(LOCK_FILE):
        print("⚠️ Bot já está em execução."); return False
    open(LOCK_FILE, "w").write(datetime.utcnow().isoformat()); return True

def limpar_instancia(): 
    if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)

def salvar_log_sinal(sinal: dict):
    with open(f"{LOG_DIR}/sinais.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(sinal, ensure_ascii=False) + "\n")

def gerar_grafico():
    acertos = [1 if v >= VELA_MINIMA else 0 for v in VELAS]
    plt.figure(figsize=(10,3)); plt.plot(acertos, marker="o")
    plt.grid(True, linestyle=":"); plt.title("Acertos (≥1.99x)")
    plt.tight_layout(); plt.savefig(f"{STATIC_DIR}/chart.png"); plt.close()

VELA_REGEX = re.compile(r"(\d+(?:\.\d+)?)[xX]")
def extrair_velas(html:str) -> List[float]:
    return [float(m.group(1)) for m in VELA_REGEX.finditer(html)]

def prever_proxima_entrada(seq)->Tuple[bool,float]:
    if len(seq)<2: return False,0.0
    if seq[-1]<2 and seq[-2]<2:
        prob=90+round((2-seq[-1])*5+(2-seq[-2])*5,1)
        return True,min(prob,99.9)
    return False,0.0
# ======================================

# -------------- HTTP ------------------
async def obter_html(session:aiohttp.ClientSession)->str:
    try:
        async with session.get(GAME_URL, timeout=10) as r:
            return await r.text()
    except Exception as e:
        print("[HTML ERR]",e); return ""
# ======================================

# ------ ENVIO TELEGRAM ----------------
async def enviar_sinal(sinal):
    global ULTIMO_ENVIO_ID
    mid=f"{sinal['timestamp']}-{sinal['multiplicador']}"
    if mid==ULTIMO_ENVIO_ID: return
    ULTIMO_ENVIO_ID=mid

    texto = (
        "🎰 <b>SINAL DETECTADO - AVIATOR</b>\n\n"
        f"🕐 <b>Hora:</b> {sinal['hora']}\n"
        f"🎯 <b>Multiplicador:</b> <code>{sinal['multiplicador']}x</code>\n"
        f"📊 <b>Classificação:</b> {sinal['tipo']}\n"
        f"🔮 <b>Previsão:</b> {sinal['previsao']}\n\n"
        f"{sinal['mensagem'] or ''}\n\n"
        f"💰 Cadastre-se:\n👉 <a href='{BANNER_LINK}'>{BANNER_LINK}</a>"
    )
    mk = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Cadastre-se", url=BANNER_LINK)]])
    for dest in (GRUPO_ID, CHAT_ID):
        try:
            await bot.send_photo(dest, photo=BANNER_IMAGEM, caption=texto, reply_markup=mk)
        except Exception as e:
            print("[SEND ERR]",e)

async def enviar_grafico_auto(forcado=False):
    global ULTIMO_GRAFICO
    agora=datetime.now(LUANDA_TZ)
    if not forcado and ULTIMO_GRAFICO and (agora-ULTIMO_GRAFICO).total_seconds()<GRAPH_INTERVAL_SEC:
        return
    if not VELAS: return
    ULTIMO_GRAFICO=agora; gerar_grafico()
    mk=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Cadastre-se",url=BANNER_LINK)]])
    for dest in (GRUPO_ID,CHAT_ID):
        try:
            await bot.send_photo(dest, photo=FSInputFile(f"{STATIC_DIR}/chart.png"),
                                 caption=f"📈 <b>Gráfico automático</b> — {agora.strftime('%d/%m %H:%M')}",
                                 reply_markup=mk)
        except Exception as e: print("[GRAF ERR]",e)
# ======================================

# ------------- HANDLERS ---------------
@router.message(Command("start"))  async def _start(m:Message): await m.answer("🚀 Bot Voo Milionário online! /ajuda")
@router.message(Command("ajuda"))  async def _help(m:Message):  await m.answer("Comandos: /start /ajuda /grafico /sinais /status /painel /sobre")
@router.message(Command("grafico"))async def _graf(m:Message):  await enviar_grafico_auto(forcado=True)

@router.message(Command("sinais"))
async def _sig(m:Message):
    arq=f"{LOG_DIR}/sinais.jsonl"
    if not os.path.exists(arq): await m.answer("Nenhum sinal."); return
    linhas=open(arq,encoding="utf-8").read().strip().splitlines()[-5:]
    if not linhas: await m.answer("Nenhum sinal."); return
    resp="\n".join(f"<b>{json.loads(l)['hora']}</b> — {json.loads(l)['multiplicador']}x" for l in linhas)
    await m.answer("📌 <b>Últimos sinais</b>:\n"+resp)

@router.message(Command("status"))
async def _status(m:Message):
    await m.answer(f"VELAS: {len(VELAS)} • Último mult: {ULTIMO_MULT} • Último gráfico: {ULTIMO_GRAFICO}")

@router.message(Command("painel")) async def _pan(m:Message): await m.answer("📊 Painel em construção.")
@router.message(Command("sobre"))  async def _sob(m:Message): await m.answer("🤖 Voo Milionário Bot — by Pio.")

# --------------- LOOP -----------------
async def monitorar():
    global ULTIMO_MULT
    async with aiohttp.ClientSession() as sess:
        while True:
            try:
                html=await obter_html(sess)
                if not html: await asyncio.sleep(10); continue
                velas=extrair_velas(html)
                if not velas: await asyncio.sleep(10); continue
                nova=velas[-1]
                if nova!=ULTIMO_MULT:
                    VELAS.append(nova); VELAS=VELAS[-20:]; ULTIMO_MULT=nova
                    hora=datetime.now(LUANDA_TZ).strftime("%H:%M:%S")
                    prever,chance=prever_proxima_entrada(VELAS)
                    tipo="🔥 Alta (≥1.99x)" if nova>=VELA_MINIMA else "🢨 Baixa (<1.99x)"
                    msg=None
                    if nova>=VELA_RARA:
                        tipo="🚀 Rara (>100x)"
                        msg=MENSAGENS_MOTIVAS[int(datetime.now().timestamp())%len(MENSAGENS_MOTIVAS)]
                    sinal={"hora":hora,"multiplicador":nova,"tipo":tipo,
                           "previsao":f"{chance}%" if prever else "Sem sinal",
                           "mensagem":msg,"timestamp":datetime.utcnow().isoformat()}
                    salvar_log_sinal(sinal); await enviar_sinal(sinal)
                await enviar_grafico_auto()
                await asyncio.sleep(5)
            except Exception as e:
                print("[LOOP ERR]",e); await asyncio.sleep(10)

# ---------- COMANDOS BOT -------------
async def registrar_comandos():
    cmds=[("start","Iniciar"),("ajuda","Ajuda"),("sinais","Últimos"),("grafico","Gráfico"),
          ("status","Status"),("painel","Painel"),("sobre","Sobre")]
    await bot.set_my_commands([BotCommand(c,d) for c,d in cmds])

# --------------- MAIN ----------------
async def iniciar_scraping():
    if not checar_instancia(): return
    try:
        await registrar_comandos()
        asyncio.create_task(monitorar())
        await dp.start_polling(bot)
    finally:
        limpar_instancia()

if __name__=="__main__":
    asyncio.run(iniciar_scraping())
    # Porta fake p/ Render free
    if os.getenv("RENDER"):
        port=int(os.getenv("PORT",10000))
        with socket.socket() as s:
            s.bind(("0.0.0.0",port)); s.listen()
            print(f"[RENDER] Escutando porta {port} (fake)"); s.accept()
