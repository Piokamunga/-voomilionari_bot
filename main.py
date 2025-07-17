""" main.py – VOO MILIONÁRIO (HTML + WebSocket + Webhook Telegram) """

import asyncio
from aiohttp import web

from save_html_loop import loop_salvar_html
from telegrambotpy import iniciar_bot
from extract_ws_url import atualizar_ws_url_no_script  # 🧠 Atualiza URL WS dinâmico

# === ROTA DE STATUS PARA MONITORAMENTO ===
async def health_check(request):
    return web.Response(text="✅ Bot VOO MILIONÁRIO Online via HTML + WS + Webhook")

# === INICIALIZAÇÃO DE TODAS AS TAREFAS ===
async def start_all():
    await atualizar_ws_url_no_script()  # Extrai e atualiza URL do WebSocket automaticamente

    await asyncio.gather(
        loop_salvar_html(),  # Loop scraping HTML
        iniciar_bot(),       # Inicia o bot Telegram via webhook
    )

# === APP HTTP PARA RENDER ===
def main():
    app = web.Application()
    app.router.add_get("/", health_check)  # http://...:10000 para ver o status

    loop = asyncio.get_event_loop()
    loop.create_task(start_all())         # Inicia scraping + bot

    web.run_app(app, port=10000)          # Porta para Render escutar

if __name__ == "__main__":
    main()
