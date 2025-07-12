""" save_html_loop.py – Coleta do HTML do Aviator """

import os
import re
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import asyncio

url = "https://m.goldenbet.ao/gameGo?id=1873916590817091585&code=2201&platform=PP"

def configurar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    return webdriver.Chrome(service=Service(), options=chrome_options)

async def loop_salvar_html():
    os.makedirs("logs", exist_ok=True)
    driver = configurar_driver()
    while True:
        try:
            driver.get(url)
            await asyncio.sleep(5)
            html = driver.page_source
            nome_arquivo = f"logs/html_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
            with open(nome_arquivo, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception as e:
            print(f"[ERRO HTML] {e}")
        await asyncio.sleep(15)
