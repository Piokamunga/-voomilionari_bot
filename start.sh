#!/bin/bash

echo "[⬆️] Atualizando pip..."
pip install --upgrade pip

echo "[⬇️] Reinstalando dependências Python..."
pip install --upgrade --force-reinstall -r requirements.txt

echo "[✅] Aplicando patch do undetected-chromedriver..."
python -m undetected_chromedriver.patcher || echo "[⚠️] Aviso: Chromium patch falhou, mas pode continuar."

# Remova ou mantenha conforme sua necessidade:
# echo "[🔄] Buscando WebSocket atualizado do Aviator..."
# python extract_ws_url.py || echo "[⚠️] Aviso: Não foi possível atualizar WebSocket."

echo "[🚀] Iniciando o bot VOO MILIONÁRIO..."
exec python telegrambotpy.py
