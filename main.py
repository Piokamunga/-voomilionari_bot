import asyncio
from aiohttp import web
from telegrambotpy.py import iniciar_scraping

async def iniciar_servidor():
    async def handle(request):
        return web.Response(text="Bot Aviator rodando 24/7 no Render! 🚀")

    app = web.Application()
    app.add_routes([web.get('/', handle)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)  # Porta 10000 (defina essa porta no Render também)
    await site.start()
    print("Servidor HTTP iniciado na porta 10000")

async def main():
    # Executa scraper e servidor HTTP paralelamente
    await asyncio.gather(
        iniciar_scraping(),
        iniciar_servidor()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⛔ Encerrado manualmente.")
    except Exception as e:
        print(f"[ERRO GERAL] {e}")
