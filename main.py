import asyncioAdd commentMore actions
from aiohttp import web
from telegrambotpy.py import iniciar_scraping
from telegrambotpy import iniciar_scraping

async def iniciar_servidor():
    async def handle(request):
        return web.Response(text="🤖 Bot Voo Milionário rodando 24/7! Tudo no piloto automático 🚀")

    app = web.Application()
    app.add_routes([web.get('/', handle)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)  # Porta configurável na Render
    await site.start()
    print("🌐 Servidor HTTP iniciado na porta 10000")

async def main():
    await asyncio.gather(
        iniciar_scraping(),
        iniciar_servidor()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
