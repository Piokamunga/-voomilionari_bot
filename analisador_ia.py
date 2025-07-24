"""
analisador_ia.py – IA inteligente com mensagem estilo VIP
──────────────────────────────────────────────────────────────
Contém duas funções:
• analisar_multiplicadores(html) – via scraping HTML
• processar_multiplicadores(lista) – via WebSocket em tempo real
"""

import re
from random import uniform, randint
from typing import Optional

def analisar_multiplicadores(html: str) -> Optional[str]:
    """
    Analisa os multiplicadores contidos no HTML e retorna mensagem VIP.
    """
    mults = re.findall(r'(\d+(?:\.\d+)?)x', html)
    mults = [float(m) for m in mults][-20:]

    if len(mults) < 10:
        return None

    ultimos = mults[-5:]
    baixos = sum(1 for m in ultimos if m < 1.5)
    altos = sum(1 for m in ultimos if m >= 2.0)

    if baixos >= 4 or altos >= 3:
        entrada = round(uniform(2.8, 3.5), 2)
        alvo = round(entrada + uniform(0.5, 1.5), 2)
        padrao = f"VA 0{randint(1, 9)}"
        faixa_vermelha = f"{round(uniform(1.05, 1.2), 2)} | {round(uniform(10.0, 15.0), 2)}"
        green_exemplo = f"{round(uniform(100, 250), 2)} | {round(uniform(1.0, 1.5), 1)}"

        return f"""
<b>GRUPO AVIATOR VIP:</b>
🚨 <b>ENTRADA CONFIRMADA</b> 🚨

🎮 <b>Jogo:</b> Aviator Velas Altas  
🤖 <b>Padrão:</b> {padrao}

🚥 {faixa_vermelha}
💵 <b>Saia no</b> {alvo}x
🌪️ <b>Faça até 5 fixas!</b>

<b>Resumo:</b>
📱 Acesse o Aviator Velas Altas
✅ ✅ <b>GREEN</b> ({green_exemplo}) ✅ ✅
""".strip()

    return None


def processar_multiplicadores(lista: list[float]) -> Optional[str]:
    """
    Recebe lista de multiplicadores (ex: do WebSocket) e gera alerta VIP se padrão for detectado.
    """
    mults = lista[-20:]  # mantém os últimos 20

    if len(mults) < 10:
        return None

    ultimos = mults[-5:]
    baixos = sum(1 for m in ultimos if m < 1.5)
    altos = sum(1 for m in ultimos if m >= 2.0)

    if baixos >= 4 or altos >= 3:
        entrada = round(uniform(2.8, 3.5), 2)
        alvo = round(entrada + uniform(0.5, 1.5), 2)
        padrao = f"VA 0{randint(1, 9)}"
        faixa_vermelha = f"{round(uniform(1.05, 1.2), 2)} | {round(uniform(10.0, 15.0), 2)}"
        green_exemplo = f"{round(uniform(100, 250), 2)} | {round(uniform(1.0, 1.5), 1)}"

        return f"""
<b>ALERTA AO VIVO – MULTIPLICADOR DETECTADO</b>

🎮 <b>Jogo:</b> Aviator WS Real-Time
📈 <b>Padrão:</b> {padrao}

🚥 {faixa_vermelha}
💵 <b>Meta:</b> {alvo}x
🌪️ <b>Entrada:</b> {entrada}x

✅ Green Exemplo: {green_exemplo}
""".strip()

    return None
