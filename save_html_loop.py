"""
save_html_loop.py – Background worker para Render (auto‑regex v2)
────────────────────────────────────────────────────────────────
Baixa periodicamente o HTML do Aviator, escolhe automaticamente o
melhor regex para capturar multiplicadores com base no padrão visual
observado (ex.: 3,60x, 16,45x, 1x) e salva o HTML bruto em logs/.

• Serviço ideal: Render Background Worker (FREE)
• Variáveis de ambiente suportadas
  GAME_URL         link do Aviator (opcional)
  SCRAPE_INTERVAL  segundos entre coletas (default 30)
  DEBUG            1 imprime info extra (default 0)
"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime
from typing import Dict, Pattern

import aiohttp

# ╭───────────────────────── configuração ──────────────────────────────╮
GAME_URL = os.getenv(
    "GAME_URL",
    "https://m.goldenbet.ao/gameGo?id=1873916590817091585&code=2201&platform=PP",
)
INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "30"))  # segundos
DEBUG = os.getenv("DEBUG", "0") == "1"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/124.0"
    )
}

# Padrões de multiplicador possíveis (regex ➜ descrição)
CANDIDATE_REGEXES: Dict[str, str] = {
    # Padrão visual visto no screenshot: 1x, 2,34x, 99,24x etc.
    r"\b(\d{1,3}(?:,\d{2})?)x\b": "visual: XX,YYx ou XXx",
    # JSON "multiplier": "2.31"
    r'"multiplier"\s*:\s*"?(\d+(?:[.,]\d+)?)': 'JSON "multiplier": valor',
    # atributo data-value="2.31"
    r'data-value\s*=\s*"(\d+(?:[.,]\d+)?)"': 'data-value="valor"',
}
VELA_REGEX: Pattern | None = None  # será definido em runtime

os.makedirs("logs", exist_ok=True)

# ╭────────────────────── utilidades regex ─────────────────────────────╮

def detectar_melhor_regex(html: str) -> Pattern | None:
    """Seleciona o regex que capturar mais ocorrências no HTML recebido."""
    vencedora = None
    max_hits = 0
    desc = ""
    for pat, descr in CANDIDATE_REGEXES.items():
        hits = len(re.findall(pat, html, flags=re.I))
        if hits > max_hits:
            max_hits = hits
            vencedora = re.compile(pat, flags=re.I)
            desc = descr
    if vencedora and DEBUG:
        print(f"[AUTO‑REGEX] Selecionado: {desc} ({max_hits} ocorrências)")
    return vencedora

# ╭────────────────────── rotina principal ─────────────────────────────╮
async def fetch_and_save(session: aiohttp.ClientSession) -> None:
    global VELA_REGEX

    async with session.get(GAME_URL, headers=HEADERS, timeout=15) as resp:
        html = await resp.text()

    # Define regex se ainda não houver ou se não capturou nada
    if VELA_REGEX is None or not VELA_REGEX.search(html):
        VELA_REGEX = detectar_melhor_regex(html)
        if VELA_REGEX is None:
            print("[WARN] Nenhum padrão encontrou multiplicadores – reveja GAME_URL")

    # Salva HTML bruto
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    fname = f"logs/html_{ts}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(html)

    # Trechos úteis (máx 5) para debug
    trechos: list[str] = []
    for lin in html.splitlines():
        if ("x" in lin or "multiplier" in lin) and len(lin) < 500:
            trechos.append(lin.strip())
            if len(trechos) == 5:
                break

    # Extrai multiplicadores
    velas = [float(v.replace(",", ".")) for v in VELA_REGEX.findall(html)] if VELA_REGEX else []

    # Logs enxutos
    print(f"[SAVE] {fname} – {len(velas)} multiplicadores detectados")
    if trechos:
        for i, trecho in enumerate(trechos, 1):
            print(f"[TRECHO {i}] {trecho}")
    if velas:
        print(f"[EXTRAÇÃO] Últimos valores: {velas[-3:]}")
    if DEBUG:
        print(f"[DEBUG] HTML len={len(html)}; intervalo={INTERVAL}s")

# ╭──────────────────────────── loop ───────────────────────────────────╮
async def run_loop() -> None:
    print(f"[WORKER] save_html_loop iniciado – intervalo: {INTERVAL}s")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await fetch_and_save(session)
            except Exception as exc:
                print("[ERRO]", exc)
            await asyncio.sleep(INTERVAL)

# ╭──────────────────────── entry‑point ────────────────────────────────╮
if __name__ == "__main__":
    asyncio.run(run_loop())
