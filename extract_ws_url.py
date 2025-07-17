""" extract_ws_url.py – Extrai WebSocket do Aviator e atualiza o script automaticamente no Render """

from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
import time
import re
import asyncio

URL_AVIATOR = "https://m.goldenbet.ao/gameGo?id=1873916590817091585&code=2201&platform=PP"
ALVO_ARQUIVO = "save_html_loop_ws.py"

def configurar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=chrome_options, seleniumwire_options={"disable_encoding": True})

def obter_websocket():
    driver = configurar_driver()
    driver.get(URL_AVIATOR)
    time.sleep(15)

    for req in driver.requests:
        if req.url.startswith("wss://") and "spribe" in req.url:
            driver.quit()
            return req.url
    driver.quit()
    return None

async def atualizar_ws_url_no_script():
    print("[🔄] Buscando WebSocket da página do Aviator...")
    nova_url = obter_websocket()

    if not nova_url:
        print("❌ Nenhum WebSocket encontrado.")
        return

    print(f"[✅] WebSocket encontrado: {nova_url}")

    try:
        with open(ALVO_ARQUIVO, "r", encoding="utf-8") as f:
            conteudo = f.read()

        novo_conteudo = re.sub(r'URL_WS\s*=\s*".+?"', f'URL_WS = "{nova_url}"', conteudo)

        with open(ALVO_ARQUIVO, "w", encoding="utf-8") as f:
            f.write(novo_conteudo)

        print("[💾] save_html_loop_ws.py atualizado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao atualizar o arquivo: {e}")

if __name__ == "__main__":
    asyncio.run(atualizar_ws_url_no_script())
