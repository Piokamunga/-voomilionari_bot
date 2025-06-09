import asyncio
import random
import logging
from datetime import datetime
import os
from telegram import Bot

# Token e Chat ID fixos
TELEGRAM_BOT_TOKEN = "7585234067:AAF1xfSbMCh7LOckXViD2_iUfKig7GYgwO4"
TELEGRAM_CHAT_ID = "8101413562"
TELEGRAM_GRUPO_ID = os.getenv("-1002769928832")

logging.basicConfig(level=logging.INFO)

# Simula leitura de velas
def gerar_velas_falsas():
    return [round(random.uniform(0.5, 5.0), 2) for _ in range(20)]

# Envio de sinal
async def enviar_sinal(bot, velas):
    agora = datetime.now().strftime("%H:%M:%S")
    texto = f"""
📡 SINAL DE TESTE ENVIADO!
🕒 Horário: {agora}
📊 Últimas velas: {velas[-5:]}
🎯 Aposta recomendada: Próxima rodada!
✅ Probabilidade: 99%
"""
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=texto)
    logging.info("[TESTE] Sinal enviado ao chat pessoal")

# Loop principal
async def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    while True:
        velas = gerar_velas_falsas()
        logging.info(f"[TESTE] Velas simuladas: {velas[-5:]}")
        await enviar_sinal(bot, velas)
        await asyncio.sleep(10)  # Teste: 1 sinal a cada 10 segundos

if __name__ == "__main__":
    asyncio.run(main())
