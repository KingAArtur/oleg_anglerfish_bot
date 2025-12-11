import logging
import asyncio

from bot import Bot


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    bot = Bot()
    try:
        bot.start()
        asyncio.run(bot.shutdown())
    except Exception as e:
        logger.error("\n".join(e.args))
        asyncio.run(bot.shutdown())
