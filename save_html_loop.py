"""
save_html_loop.py – Background worker para Render
──────────────────────────────────────────────────
Baixa periodicamente o HTML do Aviator e salva em logs/,
além de exibir no console os multiplicadores detectados.

• Serviço ideal: Render Background Worker (FREE)
• Variáveis de ambiente suportadas:

GAME_URL         (opcional) link do Aviator
SCRAPE_INTERVAL  (opcional) segundos entre coletas (default 30)
DEBUG            1 imprime info extra (default 0)
"""

import asyncio
import os
import re
from datetime import datetime

import aiohttp

# ╭───────────────────────── configuração ─────────────────────────────╮
GAME_URL: str = os.getenv(
    "GAME_URL",
    "https://m.goldenbet.ao/gameGo?id=1873916590817091585&code=2201&platform=PP"
)
INTERVAL: int = int(os.getenv("SCRAPE_INTERVAL", "30"))  # segundos entre coletas
DEBUG: bool = os.getenv("DEBUG", "0") == "1"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/124.0"
    )
}

# Regex simples – ajuste depois que identificar o formato real no HTML
VELA_REGEX = re.compile(r'"multiplier"\s*:\s*"?(\d+(?:[.,]\d+)?)', flags=re.I)

# Garante diretório de logs
os.makedirs("logs", exist_ok=True)

# ╭───────────────────── funções principais ───────────────────────────╮
async def fetch_and_save(session: aiohttp.ClientSession) -> None:
    """Faz GET no GAME_URL, salva HTML e exibe trechos e multiplicadores."""
    async with session.get(GAME_URL, headers=HEADERS, timeout=15) as resp:
        html = await resp.text()

    # Salva o HTML bruto
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    fname = f"logs/html_{ts}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(html)

    # Coleta até 5 linhas candidatas a conter multiplicadores
    trechos: list[str] = []
    for linha in html.splitlines():
        if ("x" in linha or "multiplier" in linha) and len(linha) < 500:
            trechos.append(linha.strip())
        if len(trechos) >= 5:
            break

    # Extrai multiplicadores pelo regex atual
    velas = [float(v.replace(",", ".")) for v in VELA_REGEX.findall(html)]

    # Prints compactos
    print(f"[SAVE] {fname} – {len(velas)} multiplicadores detectados")
    if trechos:
        for i, trecho in enumerate(trechos, 1):
            print(f"[TRECHO {i}] {trecho}")
    if velas:
        print(f"[EXTRAÇÃO] Últimos 3 multiplicadores: {velas[-3:]}")
    if DEBUG:
        print(f"[DEBUG] HTML len = {len(html)}; intervalo = {INTERVAL}s")

# ╭──────────────────────────── loop ──────────────────────────────────╮
async def run_loop() -> None:
    """Loop infinito que executa fetch_and_save() a cada INTERVAL segundos."""
    print(f"[WORKER] save_html_loop iniciado – intervalo: {INTERVAL}s")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await fetch_and_save(session)
            except Exception as exc:
                print("[ERRO]", exc)
            await asyncio.sleep(INTERVAL)

# ╭────────────────────────── entry‑point ─────────────────────────────╮
if __name__ == "__main__":
    asyncio.run(run_loop())
