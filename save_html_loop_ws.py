""" save_html_loop_ws.py – WebSocket Spribe para Aviator (automatizado) """

import asyncio
import websockets
from datetime import datetime
import os

# ⚠️ Este valor será substituído automaticamente por extract_ws_url.py
URL_WS = "wss://spribe-host"  # Substituirá automaticamente com o real

async def loop_websocket():
    os.makedirs("logs", exist_ok=True)
    while True:
        try:
            print(f"[WS] Conectando a {URL_WS} ...")
            async with websockets.connect(URL_WS) as ws:
                print("[WS] Conectado com sucesso!")
                while True:
                    msg = await ws.recv()
                    if "coefficient" in msg:
                        agora = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                        nome_arquivo = f"logs/ws_{agora}.json"
                        with open(nome_arquivo, "w", encoding="utf-8") as f:
                            f.write(msg)
                        print(f"[WS] Mensagem salva: {nome_arquivo}")
        except Exception as e:
            print(f"[ERRO WS] {e}")
            await asyncio.sleep(5)
