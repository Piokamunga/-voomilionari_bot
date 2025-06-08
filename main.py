import asyncio
from goldenbet_scraper import iniciar_scraping
from telegrambotpy.telegram_bot import iniciar_bot

async def main():
    await asyncio.gather(
        iniciar_scraping(),
        iniciar_bot()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⛔ Encerrado manualmente.")
    except Exception as e:
        print(f"[ERRO GERAL] {e}")
