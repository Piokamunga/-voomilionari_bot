#!/bin/bash

echo "[⬆️] Atualizando pip..."
pip install --upgrade pip

echo "[⬇️] Reinstalando dependências Python (forçando upgrade)..."
pip install --upgrade --force-reinstall -r requirements.txt

echo "[✅] Instalando Chromium headless compatível via pip..."
python -m undetected_chromedriver.patcher || echo "[⚠️] Aviso: Chromium patch falhou mas pode continuar."

echo "[🔄] Buscando WebSocket atualizado do Aviator..."
python extract_ws_url.py

echo "[🚀] Iniciando o bot VOO MILIONÁRIO"
exec python main.py
