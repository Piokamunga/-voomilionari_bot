"""
save_html_loop.py – Scraper HTML Aviator com regex inteligente
───────────────────────────────────────────────────────────────
Captura o HTML do Aviator periodicamente e extrai multiplicadores
com base no padrão visual detectado (ex: "3,25x", "18,90x", "1x").

Ideal para uso paralelo ao WebSocket como backup/validação.

Usar no Render:
• Tipo: Background Worker
• Comando: python save_html_loop.py
"""

from __future__ import annotations
import asyncio
import os
import re
from datetime import datetime
from typing import Pattern

import aiohttp

# ╭──────────────────── configuração ─────────────────────╮
GAME_URL = os.getenv("GAME_URL", "https://m.goldenbet.ao/gameGo?id=...")
INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "30"))  # segundos
DEBUG = os.getenv("DEBUG", "0") == "1"
os.makedirs("logs", exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/124.0"
    )
}

# Candidatos a regex
CANDIDATE_REGEXES = {
    r"\b(\d{1,3}(?:,\d{1,2})?)x\b": "Padrão visual: 3,50x / 2x",
    r'"multiplier"\s*:\s*"?(\d+(?:[.,]\d+)?)': 'JSON: "multiplier": 2.31',
    r'data-value\s*=\s*"(\d+(?:[.,]\d+)?)"': 'HTML: data-value="2.31"',
}

VELA_REGEX: Pattern | None = None

# ╭────────── função: detectar melhor padrão ───────────╮
def detectar_melhor_regex(html: str) -> Pattern | None:
    max_hits = 0
    vencedora = None
    for padrao, descricao in CANDIDATE_REGEXES.items():
        hits = len(re.findall(padrao, html))
        if hits > max_hits:
            max_hits = hits
            vencedora = re.compile(padrao)
            if DEBUG:
                print(f"[AUTO-REGEX] Usando: {descricao} ({hits} ocorrências)")
    return vencedora

# ╭─────────────── função principal ───────────────╮
async def fetch_and_save(session: aiohttp.ClientSession):
    global VELA_REGEX
    try:
        async with session.get(GAME_URL, headers=HEADERS, timeout=15) as resp:
            html = await resp.text()
    except Exception as e:
        print("[ERRO REDE]", e)
        return

    # Selecionar regex mais eficaz
    if VELA_REGEX is None or not VELA_REGEX.search(html):
        VELA_REGEX = detectar_melhor_regex(html)

    # Salvar HTML bruto para análise futura
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    fname = f"logs/html_{timestamp}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(html)

    # Extrair valores
    velas = []
    if VELA_REGEX:
        velas = [float(v.replace(",", ".")) for v in VELA_REGEX.findall(html)]

    print(f"[SAVE] {fname} – {len(velas)} multiplicadores detectados")
    if DEBUG:
        for i, linha in enumerate(html.splitlines()):
            if "x" in linha and len(linha) < 500:
                print(f"[TRECHO {i+1}] {linha.strip()}")
                if i == 4:
                    break
        print(f"[DEBUG] HTML len={len(html)}; intervalo={INTERVAL}s")

# ╭────────────── loop contínuo ──────────────╮
async def fetch_and_save_loop():
    print(f"[WORKER] save_html_loop iniciado – intervalo: {INTERVAL}s")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await fetch_and_save(session)
            except Exception as e:
                print("[ERRO LOOP]", e)
            await asyncio.sleep(INTERVAL)

# ╭────────────── entry-point ───────────────╮
if __name__ == "__main__":
    asyncio.run(fetch_and_save_loop())
