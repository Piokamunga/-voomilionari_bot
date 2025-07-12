#!/bin/bash

echo "[⬆️] Atualizando pip..."
pip install --upgrade pip

echo "[🛠] Instalando Chromium e dependências..."
apt update && apt install -y chromium chromium-driver fonts-liberation

echo "[🚀] Iniciando o bot VOO MILIONÁRIO"
python main.py
