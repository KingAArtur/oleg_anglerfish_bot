import logging
import asyncio
import os

from bot import Bot


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s | %(message)s',
    datefmt='%m-%d-%Y %H:%M:%S',
    level=logging.INFO,
    filename='messages.log' if os.getenv("STAGE") == "PROD" else None,
)
logger = logging.getLogger(__name__)

# getting rid of httpx logs
logging.getLogger("httpx").setLevel(logging.WARNING)


if __name__ == "__main__":
    bot = Bot()
    try:
        bot.start()
        asyncio.run(bot.shutdown())
    except Exception as e:
        logger.error("\n".join(e.args))
        asyncio.run(bot.shutdown())
