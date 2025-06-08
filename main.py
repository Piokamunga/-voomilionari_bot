import asyncio
from goldenbet_scraper import iniciar_scraping

async def main():
    while True:
        try:
            await iniciar_scraping()
        except Exception as e:
            print(f"[ERRO AO INICIAR SCRAPING] {e}")
            await asyncio.sleep(5)  # Pequeno delay antes de tentar novamente

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⛔ Bot encerrado manualmente.")
    except Exception as e:
        print(f"[ERRO GERAL] {e}")
