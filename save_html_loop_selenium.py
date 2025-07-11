"""
save_html_loop_selenium.py – Scraper Aviator com navegador real
───────────────────────────────────────────────────────────────
Usa Chrome Headless via Selenium para capturar HTML renderizado
pelo navegador e extrair multiplicadores reais do Aviator.

✔ Ideal para páginas com JavaScript
✔ Executa scraping a cada X segundos
✔ Extrai automaticamente os multiplicadores (ex: 3,50x, 1x)

Requisitos:
• chrome/chromium + webdriver
• selenium
• render.com: ativar Chromium no build (ver docs)

Variáveis de ambiente:
────────────────────────
GAME_URL         link do Aviator (default: GoldenBet)
SCRAPE_INTERVAL  intervalo entre capturas (default: 30s)
DEBUG            ativa debug extra se = "1"
"""

from __future__ import annotations
import os
import re
import asyncio
from datetime import datetime
from typing import Pattern

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By

# ─────────────────────────────────────────────────────────────
GAME_URL = os.getenv("GAME_URL", "https://m.goldenbet.ao/gameGo?id=...")
INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "30"))  # segundos
DEBUG = os.getenv("DEBUG", "0") == "1"
os.makedirs("logs", exist_ok=True)

# ────────── Candidatos a regex de multiplicadores ────────────
CANDIDATE_REGEXES = {
    r"\b(\d{1,3}(?:,\d{1,2})?)x\b": "Visual: 3,25x ou 2x",
    r'"multiplier"\s*:\s*"?(\d+(?:[.,]\d+)?)': 'JSON: "multiplier": 2.31',
    r'data-value\s*=\s*"(\d+(?:[.,]\d+)?)"': 'HTML: data-value="2.31"',
}
VELA_REGEX: Pattern | None = None

# ─────────────────────────────────────────────────────────────
def detectar_melhor_regex(html: str) -> Pattern | None:
    """Seleciona o regex com mais acertos no HTML."""
    max_hits = 0
    selecionado = None
    for padrao, desc in CANDIDATE_REGEXES.items():
        hits = len(re.findall(padrao, html))
        if hits > max_hits:
            max_hits = hits
            selecionado = re.compile(padrao)
            if DEBUG:
                print(f"[AUTO-REGEX] Selecionado: {desc} ({hits} hits)")
    return selecionado

# ─────────────────────────────────────────────────────────────
def criar_driver() -> webdriver.Chrome:
    """Cria uma instância headless do Chrome para scraping."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,720")
    return webdriver.Chrome(options=options)

# ─────────────────────────────────────────────────────────────
async def capturar_html_e_extrair():
    global VELA_REGEX

    try:
        driver = criar_driver()
        driver.get(GAME_URL)
        await asyncio.sleep(10)  # tempo para carregar JS (ajustável)

        html = driver.page_source
        driver.quit()
    except Exception as e:
        print("[ERRO SELENIUM]", e)
        return

    # Detectar melhor regex se necessário
    if VELA_REGEX is None or not VELA_REGEX.search(html):
        VELA_REGEX = detectar_melhor_regex(html)

    # Salvar HTML para debug
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    fname = f"logs/html_{ts}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(html)

    # Extrair velas
    velas = []
    if VELA_REGEX:
        velas = [float(v.replace(",", ".")) for v in VELA_REGEX.findall(html)]

    print(f"[SAVE] {fname} – {len(velas)} multiplicadores detectados")
    if DEBUG:
        for i, linha in enumerate(html.splitlines()):
            if "x" in linha and len(linha) < 500:
                print(f"[TRECHO {i+1}] {linha.strip()}")
                if i >= 4:
                    break
        print(f"[DEBUG] HTML len={len(html)}; intervalo={INTERVAL}s")

# ─────────────────────────────────────────────────────────────
async def loop_principal():
    print(f"[WORKER] save_html_loop_selenium iniciado – intervalo: {INTERVAL}s")
    while True:
        try:
            await capturar_html_e_extrair()
        except Exception as e:
            print("[ERRO LOOP]", e)
        await asyncio.sleep(INTERVAL)

# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(loop_principal())
