import asyncio
import json
import os
import aiohttp
from datetime import datetime

SINAIS_FILE = "sinais.json"
VELA_LIMITE = 2.0
VELA_ESPECIAL = 100.0

sinais_ativos = []

async def obter_velas():
    url = "https://m.goldenbet.ao/gameGo?id=1873916590817091585&code=2201&platform=PP"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.text()
            return text

def extrair_velas(html):
    import re
    padrao = r'<div class="result-item[^"]*">([^<]+)</div>'
    valores = re.findall(padrao, html)
    return [float(v.strip('x')) for v in valores if 'x' in v]

def salvar_sinais(sinais):
    with open(SINAIS_FILE, "w") as f:
        json.dump(sinais, f)

async def iniciar_scraping():
    while True:
        try:
            html = await obter_velas()
            velas = extrair_velas(html)
            novas = []

            for valor in velas:
                if valor >= VELA_LIMITE:
                    tipo = "🔥 Alta (>2x)" if valor < VELA_ESPECIAL else "💎 Rara (>100x)"
                    sinal = {
                        "valor": valor,
                        "tipo": tipo,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
                    if sinal not in sinais_ativos:
                        sinais_ativos.append(sinal)
                        print(f"[SINAL] {sinal}")
                        novas.append(sinal)

            if novas:
                salvar_sinais(sinais_ativos[-30:])

        except Exception as e:
            print(f"[ERRO SCRAPER] {e}")
        await asyncio.sleep(10)
