"""
save_html_loop.py – Background worker para Render
──────────────────────────────────────────────────
Baixa periodicamente o HTML do Aviator e salva em logs/, além de
mostrar no console os multiplicadores encontrados.

• Serviço ideal: Render Background Worker (FREE)
• Variáveis de ambiente suportadas:
  - GAME_URL         (opcional) link do Aviator
  - SCRAPE_INTERVAL  (opcional) segundos entre coletas (default 30)
  - DEBUG            1 imprime mais info (default 0)
"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime

import aiohttp

# ╭───────────────────────── configuração ───────────────────────────────╮
GAME_URL: str = os.getenv(
    "GAME_URL",
    "https://m.goldenbet.ao/gameGo?id=1873916590817091585&code=2201&platform=PP",
)
INTERVAL: int = int(os.getenv("SCRAPE_INTERVAL", "30"))  # segundos
DEBUG: bool = os.getenv("DEBUG", "0") == "1"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/124.0"
    )
}

# regex simples que funciona na maioria das versões da página
VELA_REGEX = re.compile(r'"multiplier"\s*:\s*"?(\d+(?:[.,]\d+)?)', flags=re.I)

os.makedirs("logs", exist_ok=True)


async def fetch_and_save(session: aiohttp.ClientSession) -> str:
    async with session.get(GAME_URL, headers=HEADERS, timeout=15) as resp:
        html = await resp.text()

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    fname = f"logs/html_{ts}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(html)

    velas = [float(v.replace(",", ".")) for v in VELA_REGEX.findall(html)]
    print(f"[SAVE] {fname} – multiplicadores: {velas if velas else 'nenhum'}")
    if DEBUG:
        print(f"[DEBUG] HTML len = {len(html)}; INTERVAL = {INTERVAL}s")
    return html


async def run_loop() -> None:
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await fetch_and_save(session)
            except Exception as exc:
                print("[ERRO]", exc)
            await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
    print("[WORKER] save_html_loop iniciado – intervalo:", INTERVAL, "segundos")
    asyncio.run(run_loop())
