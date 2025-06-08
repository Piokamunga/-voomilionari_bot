import asyncio
from goldenbet_scraper import iniciar_scraping

async def main():
    await iniciar_scraping()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⛔ Encerrado manualmente.")
    except Exception as e:
        print(f"[ERRO GERAL] {e}")
