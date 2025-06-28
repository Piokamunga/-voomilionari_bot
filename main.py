import asyncio
from aiohttp import web
from telegrambotpy import iniciar_scraping  # importa a função principal do bot

# -----------------------------------------------------------------
# Servidor HTTP simples (opcional – health‑check)
# -----------------------------------------------------------------
async def iniciar_servidor():
    async def handle(request):
        return web.Response(
            text="🤖 Bot Voo Milionário rodando 24/7! Tudo no piloto automático 🚀"
        )

    app = web.Application()
    app.add_routes([web.get("/", handle)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=10000)  # porta configurável na Render
    await site.start()
    print("🌐 Servidor HTTP iniciado na porta 10000")

# -----------------------------------------------------------------
# Rotina principal: bot (polling) + servidor em paralelo
# -----------------------------------------------------------------
async def main():
    await asyncio.gather(
        iniciar_scraping(),   # inicia o bot em polling
        iniciar_servidor()    # health‑check HTTP
    )

# -----------------------------------------------------------------
# Entry‑point
# -----------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⛔ Encerrado manualmente.")
    
