#!/bin/bash

echo "[⬆️] Atualizando pip..."
pip install --upgrade pip

echo "[⬇️] Instalando dependências Python..."
pip install -r requirements.txt

echo "[✅] Instalando Chromium headless compatível via pip..."
python -m undetected_chromedriver.patcher

echo "[🔄] Buscando WebSocket atualizado do Aviator..."
python extract_ws_url.py

echo "[🚀] Iniciando o bot VOO MILIONÁRIO"
exec python main.py
