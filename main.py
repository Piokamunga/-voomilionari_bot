import asyncio
from goldenbet_scraper import iniciar_scraping
from telegram_bot import iniciar_bot
from painel import iniciar_painel

async def main():
    await asyncio.gather(
        iniciar_scraping(),
        iniciar_bot(),
        iniciar_painel()
    )

if __name__ == "__main__":
    asyncio.run(main())
