import aiohttp
import asyncio
import json
import re
from datetime import datetime
import pytz

# === CONFIGURAÇÕES ===
URL = "https://m.goldenbet.ao/gameGo?id=1873916590817091585&code=2201&platform=PP"
LUANDA_TZ = pytz.timezone("Africa/Luanda")
SINAIS_FILE = "sinais.json"

# === LIMITES DE CLASSIFICAÇÃO DAS VELAS ===
VELA_MINIMA = 2.0
VELA_RARA = 100.0
VELAS = []
ULTIMO_MULT = None
SINAIS_ATIVOS = []

# === LÓGICA DE PREVISÃO DE ENTRADA ===
def prever_proxima_entrada(ultimas):
    """Prevê entrada após 2 velas baixas (<2x)."""
    if len(ultimas) < 2:
        return False, 0
    if ultimas[-1] < 2.0 and ultimas[-2] < 2.0:
        chance = 90 + round((2.0 - ultimas[-1]) * 5 + (2.0 - ultimas[-2]) * 5, 1)
        return True, min(chance, 99.9)
    return False, 0

# === SCRAPER DE HTML ===
async def obter_html(session):
    try:
        async with session.get(URL, timeout=10) as resp:
            return await resp.text()
    except Exception as e:
        print(f"[ERRO HTML] {e}")
        return ""

def extrair_velas(html):
    """Extrai os multiplicadores (velas) do HTML da GoldenBet."""
    padrao = r'<div class="result-item[^"]*">([^<]+)</div>'
    valores = re.findall(padrao, html)
    return [float(v.strip('x')) for v in valores if 'x' in v and v.replace("x", "").replace(".", "", 1).isdigit()]

# === ARMAZENAMENTO LOCAL ===
def salvar_sinais():
    """Salva os últimos 30 sinais detectados."""
    with open(SINAIS_FILE, "w") as f:
        json.dump(SINAIS_ATIVOS[-30:], f, indent=2)

# === LOOP PRINCIPAL DE MONITORAMENTO ===
async def iniciar_scraping():
    """Executa o scraping 24h por dia em loop contínuo."""
    global ULTIMO_MULT
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                html = await obter_html(session)
                velas = extrair_velas(html)
                if not velas:
                    await asyncio.sleep(10)
                    continue

                nova = velas[-1]
                if nova != ULTIMO_MULT:
                    VELAS.append(nova)
                    if len(VELAS) > 20:
                        VELAS.pop(0)

                    ULTIMO_MULT = nova
                    hora = datetime.now(LUANDA_TZ).strftime("%H:%M:%S")
                    ts = datetime.now().isoformat()
                    prever, chance = prever_proxima_entrada(VELAS)

                    tipo = "🔥 Alta (≥2x)" if nova >= VELA_MINIMA else "🔻 Baixa (<2x)"
                    if nova >= VELA_RARA:
                        tipo = "💎 Rara (≥100x)"

                    sinal = {
                        "jogo": "Aviator",
                        "multiplicador": f"{nova:.2f}",
                        "hora": hora,
                        "timestamp": ts,
                        "tipo": tipo,
                        "previsao": f"{chance:.1f}%" if prever else "Nenhuma",
                        "mensagem": (
                            "🚀 <b>Momento ideal para entrada!</b>\n"
                            f"🎯 Aposte na próxima rodada com confiança.\n"
                            f"📊 Chance estimada: <b>{chance:.1f}%</b>"
                        ) if prever else None
                    }

                    if sinal not in SINAIS_ATIVOS:
                        SINAIS_ATIVOS.append(sinal)
                        salvar_sinais()
                        print(f"[SINAL] {hora} | {nova:.2f}x | {tipo} | Previsão: {sinal['previsao']}")

            except Exception as e:
                print(f"[ERRO LOOP SCRAPER] {e}")

            await asyncio.sleep(10)
