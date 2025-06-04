import os
import time
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# Configurações
API_TOKEN = '7585234067:AAGNX-k10l5MuQ7nbMirlsls5jugil16V38'
CHAT_ID = '8101413562'  # Enviar apenas para o chat pessoal
SEND_INTERVAL = 120  # Enviar a cada 2 minutos
LINK_AFILIADO = 'https://bit.ly/449TH4F'

# Configuração de logging
logging.basicConfig(level=logging.INFO)

# Inicializa o bot
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Dados reais de exemplo (podem ser substituídos por scraping no futuro)
resultados_fake = [
    "1.01x", "1.60x", "1.97x", "3.71x", "21.34x", "2.26x",
    "5.46x", "8.82x", "5.02x", "12.05x", "19.22x", "11.76x",
    "6.94x", "3.06x", "3.27x", "2.14x", "5.44x", "1.81x"
]

mensagens_motivacionais = [
    "✨ Aproveita o momento! Entra na próxima rodada!",
    "🚀 Não perca tempo, as melhores rodadas estão chegando!",
    "🌟 Resultado acima de 5x identificado! Hora certa pra agir!",
    "⚡ Confere o histórico! Vem lucro real!"
]

def gerar_mensagem():
    from random import sample, choice
    sinais = sample(resultados_fake, 6)
    motivacional = choice(mensagens_motivacionais)
    mensagem = (
        "🚨 NOVO SINAL DISPONÍVEL!\n\n"
        f"🔹 {sinais[0]} | {sinais[1]} | {sinais[2]}\n"
        f"🔹 {sinais[3]} | {sinais[4]} | {sinais[5]}\n\n"
        f"{motivacional}\n\n"
        f"🌐 Jogue agora: {LINK_AFILIADO}"
    )
    return mensagem

async def enviar_sinais():
    while True:
        try:
            mensagem = gerar_mensagem()
            await bot.send_message(chat_id=CHAT_ID, text=mensagem)
            await asyncio.sleep(SEND_INTERVAL)
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem: {e}")
            await asyncio.sleep(10)

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.reply("Min Bot de sinais ativos para divulgação. Aguarde os alertas automáticos aqui mesmo!")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(enviar_sinais())
    executor.start_polling(dp, skip_updates=True)
