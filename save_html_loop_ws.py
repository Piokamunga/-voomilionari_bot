"""
save_html_loop_ws.py – captura multiplicadores via WebSocket Spribe
────────────────────────────────────────────────────────────────────
Conecta-se ao endpoint de WebSocket oficial do Aviator e imprime todos
os multiplicadores em tempo real. Também salva mensagens em logs/ se
você quiser auditar depois.

• Serviço ideal: Render Background Worker (FREE) ou chamado no main.py
• Variáveis de ambiente opcionais:
    SCRAPE_INTERVAL  – segundos entre tentativas de reconexão (default: 5)
    DEBUG            – 1 ativa logs extras (default: 0)
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import os

import aiohttp
import websockets

# ╭────────────────────── configuração ─────────────────────────────╮
GAME_TOKEN_URL = "https://aviator.spribe.io/bridge/token"
WS_BASE_URL = "wss://aviator.spribe.io/bridge?token={token}"

RECONNECT_DELAY = int(os.getenv("SCRAPE_INTERVAL", "5"))
DEBUG = os.getenv("DEBUG", "0") == "1"

os.makedirs("logs", exist_ok=True)

# ╭──────────────────── obter novo token ───────────────────────────╮
async def get_token() -> str:
    """Obtém um token válido para abrir o WebSocket."""
    async with aiohttp.ClientSession() as session:
        async with session.get(GAME_TOKEN_URL, timeout=10) as resp:
            data = await resp.json()
            return data["token"]

# ╭───────────────────────── loop principal ────────────────────────╮
async def loop_ws() -> None:
    """Mantém o WebSocket aberto e imprime/salva multiplicadores."""
    while True:
        token = await get_token()
        url = WS_BASE_URL.format(token=token)
        print("[WS] Conectando ao Aviator…")

        try:
            async with websockets.connect(url, ping_interval=None) as ws:
                print("[WS] Conexão estabelecida.")
                async for msg in ws:
                    data = json.loads(msg)
                    if data.get("t") == "coefficient":
                        coef = data["v"]
                        ts = dt.datetime.utcnow().isoformat()
                        print(f"[WS] {ts} – {coef}x")

                        if DEBUG:
                            with open("logs/ws_coefficients.txt", "a", encoding="utf-8") as f:
                                f.write(f"{ts}\t{coef}\n")

        except Exception as exc:
            print("[ERRO WS]", exc)
            print(f"[WS] Tentando reconectar em {RECONNECT_DELAY}s…")
            await asyncio.sleep(RECONNECT_DELAY)

# ╭──────────────────────── entry-point ────────────────────────────╮
if __name__ == "__main__":
    asyncio.run(loop_ws())
