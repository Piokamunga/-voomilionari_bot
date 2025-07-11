"""
main.py – Orquestrador Voo Milionário (Render Web Service)
───────────────────────────────────────────────────────────
Executa em paralelo:
• Bot Telegram – telegrambotpy.py
• Health‑check HTTP na porta 10000
• Scraping HTML (save_html_loop.py)
• WebSocket tempo real (save_html_loop_ws.py)
"""

import asyncio
import os
from aiohttp import web

from telegrambotpy import iniciar_bot
from save_html_loop import fetch_and_save_loop
from save_html_loop_ws import iniciar_ws_loop

PORT = int(os.getenv("PORT", "10000"))

# ───────────── Health Check HTTP (Render exige porta aberta) ───────────── #
async def handle_health(_: web.Request) -> web.Response:
    return web.Response(text="✅ Voo Milionário Online")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=PORT)
    await site.start()
    print(f"🌐 Servidor HTTP iniciado na porta {PORT}")

# ───────────────────────────── Executor paralelo ────────────────────────── #
async def main():
    await asyncio.gather(
        iniciar_bot(),              # Telegram
        start_web_server(),         # Health check
        fetch_and_save_loop(),      # HTML scraping
        iniciar_ws_loop(),          # WebSocket Spribe
    )

if __name__ == "__main__":
    asyncio.run(main())
