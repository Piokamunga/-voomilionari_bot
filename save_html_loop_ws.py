"""
save_html_loop_ws.py – Leitor WebSocket do Aviator Spribe
──────────────────────────────────────────────────────────
Conecta em tempo real no WebSocket da Spribe e extrai multiplicadores
em tempo real, enviando sinais automaticamente via Telegram.
"""

import asyncio
import json
import websockets
from telegrambotpy import enviar_sinal

URL_WS = "wss://aviator.spribegaming.com/..."  # Substitua pela URL correta

async def processar_mensagem(data: dict):
    if "crash" in data:
        valor = data["crash"].get("point")
        if valor:
            try:
                valor = float(valor)
                print(f"[WS] Voo detectado: {valor:.2f}x")
                if valor >= 2.0:
                    await enviar_sinal(valor)
            except Exception as e:
                print("[ERRO] Conversão WebSocket:", e)

async def iniciar_ws_loop():
    print("[WS] Iniciando conexão WebSocket...")
    while True:
        try:
            async with websockets.connect(URL_WS) as ws:
                async for msg in ws:
                    try:
                        data = json.loads(msg)
                        await processar_mensagem(data)
                    except Exception as e:
                        print("[ERRO] JSON WebSocket:", e)
        except Exception as e:
            print("[ERRO] WebSocket desconectado. Reconectando em 5s...", e)
            await asyncio.sleep(5)
