import asyncio
from aiohttp import web
from telegrambotpy import app

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
        print("⛔ Bot encerrado manualmente.")
    except Exception as e:
        print(f"[ERRO GERAL] {e}")
