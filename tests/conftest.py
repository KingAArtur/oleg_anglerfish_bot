import logging
from textwrap import dedent

import pytest

from base_classes import User, Message
from src.bot import Bot, Reply, World, TextCaseChanger
from src.logger import BaseLogger


class EmptyWorld(World):
    def __init__(self):
        super().__init__()

    async def reply(self, message: Message, reply: Reply):
        pass

    async def send_text_to_any_chat(self, text: str, chat_id: int, message_thread_id: int = None):
        pass

    def is_admin(self, user: User) -> bool:
        return True


@pytest.fixture
def world() -> EmptyWorld:
    world = EmptyWorld()
    return world


@pytest.fixture
def bot(world, tmp_path) -> Bot:
    logger = BaseLogger(name="Bot")
    logger.logger.setLevel(logging.WARNING)

    bot = Bot(dir_path=tmp_path, world=world, logger=logger)
    bot.talk_module.ngram_generator.counts_per_text = {
        "text_first": {
            ("engineer",): {
                "turret": 1,
            }
        },
        "text_second": dict(),
    }
    bot.talk_module.ngram_generator.recalculate_counts()
    santa_info = dedent(
        """\
        Driller,Engineer,Gunner,Scout
        Driller,Gunner
        Driller,Scout
        """
    )
    bot.santa_module.initialize_from_str(santa_info)

    return bot


@pytest.fixture
def user() -> User:
    user = User(username="Driller")
    return user