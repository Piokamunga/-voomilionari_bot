# -*- coding: utf-8 -*-
import asyncio
import json
import os
import re
from datetime import datetime

import aiohttp
import pytz
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

# === Configurações ===
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7585234067:AAGNX-k10l5MuQ7nbMirlsls5jugil16V38")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8101413562")
GRUPO_ID = os.getenv("TELEGRAM_GRUPO_ID", "-1002520564793")
URL = "https://m.goldenbet.ao/gameGo?id=1873916590817091585&code=2201&platform=PP"
VELA_MINIMA = 2.0
VELA_RARA = 100.0
LUANDA_TZ = pytz.timezone("Africa/Luanda")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

VELAS = []
ULTIMO_ENVIO = None
ULTIMO_MULT = None


def prever_proxima_entrada(ultimas):
    if len(ultimas) < 2:
        return False, 0
    if ultimas[-1] < 2.0 and ultimas[-2] < 2.0:
        chance = 90 + round((2.0 - ultimas[-1]) * 5 + (2.0 - ultimas[-2]) * 5, 1)
        return True, min(chance, 99.9)
    return False, 0


async def obter_html(session):
    async with session.get(URL, timeout=10) as resp:
        return await resp.text()


def extrair_velas(html):
    padrao = r'<div class="result-item[^"]*">([^<]+)</div>'
    valores = re.findall(padrao, html)
    return [float(v.strip('x')) for v in valores if 'x' in v and v.replace("x", "").replace(".", "", 1).isdigit()]


async def enviar_sinal(sinal):
    texto = (
        "🎰 <b>SINAL DETECTADO - AVIATOR</b>\n\n"
        f"🕐 <b>Hora:</b> {sinal['hora']}\n"
        f"🎯 <b>Multiplicador:</b> <code>{sinal['multiplicador']}x</code>\n"
        f"📊 <b>Classificação:</b> {sinal['tipo']}\n"
        f"🔮 <b>Previsão:</b> {sinal['previsao']}\n\n"
    )
    if sinal["mensagem"]:
        texto += f"{sinal['mensagem']}\n\n"

    if float(sinal["multiplicador"]) >= VELA_RARA:
        texto += "💎 <b>Multiplicador raro detectado! Oportunidade única!</b>\n\n"

    texto += "💰 Cadastre-se e aposte com bônus:\n👉 <a href='https://bit.ly/449TH4F'>https://bit.ly/449TH4F</a>"

    try:
        await bot.send_message(GRUPO_ID, texto)
        await bot.send_message(CHAT_ID, texto)
    except Exception as e:
        print(f"[ERRO ENVIO] {e}")

    # (Opcional) Registrar sinal em arquivo
    try:
        with open("sinais.json", "a", encoding="utf-8") as f:
            json.dump(sinal, f, ensure_ascii=False)
            f.write(",\n")
    except Exception as e:
        print(f"[ERRO LOG SINAL] {e}")


async def iniciar_scraping():
    global VELAS, ULTIMO_MULT, ULTIMO_ENVIO
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                html = await obter_html(session)
                velas = extrair_velas(html)
                if not velas:
                    await asyncio.sleep(10)
                    continue

                nova = velas[-1]
                if nova != ULTIMO_MULT:
                    VELAS.append(nova)
                    if len(VELAS) > 20:
                        VELAS.pop(0)

                    ULTIMO_MULT = nova
                    hora = datetime.now(LUANDA_TZ).strftime("%H:%M:%S")
                    ts = datetime.now().isoformat()
                    prever, chance = prever_proxima_entrada(VELAS)

                    tipo = "🔥 Alta (≥2x)" if nova >= VELA_MINIMA else "🧊 Baixa (<2x)"
                    if nova >= VELA_RARA:
                        tipo = "💎 Rara (≥100x)"

                    sinal = {
                        "jogo": "Aviator",
                        "multiplicador": f"{nova:.2f}",
                        "hora": hora,
                        "timestamp": ts,
                        "tipo": tipo,
                        "previsao": f"{chance:.1f}%" if prever else "Nenhuma",
                        "mensagem": (
                            "🚀 <b>Momento ideal para entrada!</b>\n"
                            f"🎯 Aposte na próxima rodada com confiança.\n"
                            f"📈 Chance estimada: <b>{chance:.1f}%</b>"
                        ) if prever else None
                    }

                    # Evita repetição se mesmo multiplicador e previsão já foram enviados
                    if not ULTIMO_ENVIO or (
                        sinal["multiplicador"] != ULTIMO_ENVIO["multiplicador"]
                        or sinal["previsao"] != ULTIMO_ENVIO["previsao"]
                    ):
                        await enviar_sinal(sinal)
                        ULTIMO_ENVIO = sinal

                        # Log simples (opcional)
                        try:
                            with open("logs.txt", "a", encoding="utf-8") as f:
                                f.write(f"[{hora}] {sinal['multiplicador']}x | {sinal['tipo']} | Prev: {sinal['previsao']}\n")
                        except:
                            pass

            except Exception as e:
                print(f"[ERRO SCRAPER] {e}")
            await asyncio.sleep(10)


async def main():
    await asyncio.gather(
        dp.start_polling(bot),
        iniciar_scraping()
    )


if __name__ == "__main__":
    asyncio.run(main())
