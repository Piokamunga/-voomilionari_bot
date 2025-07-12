""" main.py – VOO MILIONÁRIO (Render Orquestrador) """

import asyncio
from aiohttp import web
from save_html_loop import loop_salvar_html
from save_html_loop_ws import loop_websocket
from telegrambotpy import iniciar_bot

async def health_check(request):
    return web.Response(text="✅ Bot VOO MILIONÁRIO Online")

async def start_all():
    tasks = [
        loop_salvar_html(),
        loop_websocket(),
        iniciar_bot()
    ]
    await asyncio.gather(*tasks)

def main():
    app = web.Application()
    app.router.add_get("/", health_check)
    loop = asyncio.get_event_loop()
    loop.create_task(start_all())
    web.run_app(app, port=10000)

if __name__ == "__main__":
    main()
