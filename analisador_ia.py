"""
analisador_ia.py – IA inteligente com mensagem estilo VIP
──────────────────────────────────────────────────────────────
Contém duas funções:
• analisar_multiplicadores(html) – via scraping HTML
• processar_multiplicadores(lista) – via WebSocket em tempo real
"""

import asyncio
import os
import json
import aiohttp
import websockets
from analisador_ia import processar_multiplicadores
from telegram import Bot

# ✅ Variáveis de ambiente (ajuste no Replit ou .env)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "SEU_TOKEN_AQUI")
CHAT_ID = os.getenv("CHAT_ID", "SEU_CHAT_ID_AQUI")
WEBSOCKET_URL = os.getenv("WS_URL", "wss://aviator-bets-pragmatic.softswiss.net/ws")

bot = Bot(token=TELEGRAM_TOKEN)
multiplicadores = []

async def enviar_alerta(msg: str):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="HTML")
        print("[✅] Alerta enviado com sucesso!")
    except Exception as e:
        print(f"[❌] Erro ao enviar alerta: {e}")

async def consumir_ws():
    print(f"[🌐] Conectando ao WebSocket: {WEBSOCKET_URL}")
    try:
        async with websockets.connect(WEBSOCKET_URL) as ws:
            while True:
                msg = await ws.recv()
                try:
                    data = json.loads(msg)
                    if isinstance(data, list):
                        for item in data:
                            m = item.get("crash_point")
                            if m and isinstance(m, (int, float)):
                                multiplicadores.append(float(m))
                                print(f"[📈] Novo multiplicador: {m}x")

                                alerta = processar_multiplicadores(multiplicadores)
                                if alerta:
                                    await enviar_alerta(alerta)

                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"[❌] Erro no WebSocket: {e}")
        await asyncio.sleep(10)
        await consumir_ws()  # reconectar automaticamente

async def main():
    await consumir_ws()

if __name__ == "__main__":
    asyncio.run(main())
