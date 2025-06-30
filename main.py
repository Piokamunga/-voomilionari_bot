import asyncio
from aiohttp import web

from telegrambotpy import iniciar_scraping          # bot em polling
from save_html_loop import run_loop as salvar_html  # loop que grava HTML

# -----------------------------------------------------------------
# Servidor HTTP simples (health-check)
# -----------------------------------------------------------------
async def iniciar_servidor() -> None:
    async def handle(request):
        return web.Response(
            text="🤖 Bot Voo Milionário rodando 24/7! Tudo no piloto automático 🚀"
        )

    app = web.Application()
    app.add_routes([web.get("/", handle)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=10000)
    await site.start()
    print("🌐 Servidor HTTP iniciado na porta 10000")


# -----------------------------------------------------------------
# Rotina principal: bot + servidor + salvador de HTML
# -----------------------------------------------------------------
async def main() -> None:
    await asyncio.gather(
        iniciar_scraping(),   # bot Telegram em polling
        iniciar_servidor(),   # health-check HTTP
        salvar_html(),        # salva HTML do Aviator em loop
    )


# -----------------------------------------------------------------
# Entry-point
# -----------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⛔ Encerrado manualmente.")
