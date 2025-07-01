"""
main.py – Orquestrador Voo Milionário (Render Web Service)
───────────────────────────────────────────────────────────
Executa em paralelo:
• Bot Telegram (polling) – telegrambotpy.py
• Health‑check HTTP na porta 10000
• Loop WebSocket Spribe (save_html_loop_ws.py) que recebe multiplicadores em tempo real
"""

from __future__ import annotations

import asyncio
from aiohttp import web

from telegrambotpy import iniciar_scraping          # bot Telegram em polling
from save_html_loop_ws import loop_ws as salvar_html  # loop WebSocket em tempo real

# ╭────────────────────────── Servidor HTTP health-check ─────────────────────────╮
async def iniciar_servidor() -> None:
    async def handle(request):
        return web.Response(
            text="🤖 Voo Milionário rodando com WebSocket! 🚀"
        )

    app = web.Application()
    app.add_routes([web.get("/", handle)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=10000)
    await site.start()
    print("🌐 Health‑check HTTP iniciado em http://0.0.0.0:10000/")


# ╭──────────────────────────── Rotina principal ─────────────────────────────╮
async def main() -> None:
    await asyncio.gather(
        iniciar_scraping(),   # bot Telegram (polling)
        iniciar_servidor(),   # health-check HTTP
        salvar_html(),        # WebSocket Spribe (multiplicadores)
    )


# ╭──────────────────────────── Entry-point ─────────────────────────────╮
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⛔ Encerrado manualmente.")
