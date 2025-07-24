"""
main.py – Orquestrador Voo Milionário (HTML + Selenium + WebSocket + Webhook Telegram)
────────────────────────────────────────────────────────────────────────────────────────────
Executa:
• Scraping via HTML (save_html_loop.py)
• Scraping via Selenium (save_html_loop_selenium.py)
• Captura de multiplicadores via WebSocket (save_html_loop_ws.py)
• Bot Telegram via webhook (telegrambotpy.py)
• Atualização dinâmica do WebSocket (extract_ws_url.py)
• Health check HTTP (porta definida por $PORT para Render)
"""

import os
import asyncio
from aiohttp import web

# ───── IMPORTAÇÕES DOS MÓDULOS INTERNOS ───── #
from save_html_loop import loop_salvar_html
from save_html_loop_selenium import loop_salvar_html_selenium
from save_html_loop_ws import loop_websocket
from telegrambotpy import iniciar_bot
from extract_ws_url import atualizar_ws_url_no_script

# ───── ROTA DE SAÚDE PARA MONITORAMENTO (Render) ───── #
async def health_check(request):
    return web.Response(text="✅ Voo Milionário Online – HTML + Selenium + WS + Telegram")

# ───── INICIALIZAÇÃO ASSÍNCRONA DE TODOS OS PROCESSOS ───── #
async def start_all():
    try:
        await atualizar_ws_url_no_script()  # Atualiza automaticamente o WebSocket extraído
    except Exception as e:
        print(f"[⚠️] Falha ao atualizar WebSocket automaticamente: {e}")

    await asyncio.gather(
        loop_salvar_html(),           # Coleta via HTML estático (requests)
        loop_salvar_html_selenium(),  # Coleta via HTML dinâmico (Selenium)
        loop_websocket(),             # Escuta WebSocket em tempo real
        iniciar_bot(),                # Bot Telegram via webhook
    )

# ───── FUNÇÃO PRINCIPAL ───── #
def main():
    port = int(os.environ.get("PORT", 10000))  # Compatível com Render

    app = web.Application()
    app.router.add_get("/", health_check)

    loop = asyncio.get_event_loop()
    loop.create_task(start_all())

    web.run_app(app, port=port)

if __name__ == "__main__":
    main()
