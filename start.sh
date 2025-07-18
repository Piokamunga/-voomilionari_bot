#!/bin/bash

echo "[⬆️] Atualizando pip..."
pip install --upgrade pip

echo "[⬇️] Instalando dependências do sistema..."
apt-get update && apt-get install -y chromium wget unzip xvfb

echo "[⬇️] Reinstalando dependências Python (forçando upgrade)..."
pip install --upgrade --force-reinstall -r requirements.txt

echo "[✅] Aplicando patch do undetected-chromedriver..."
python -m undetected_chromedriver.patcher || echo "[⚠️] Aviso: Chromium patch falhou, mas pode continuar."

echo "[🔄] Buscando WebSocket atualizado do Aviator..."
python extract_ws_url.py || echo "[⚠️] Aviso: Não foi possível atualizar WebSocket."

echo "[🚀] Iniciando o bot VOO MILIONÁRIO..."
exec python main.py
