import asyncio
import logging

from routes.telegram import run_telegram_poller


logging.basicConfig(level=logging.INFO)


async def main() -> None:
    await run_telegram_poller()


if __name__ == "__main__":
    asyncio.run(main())
