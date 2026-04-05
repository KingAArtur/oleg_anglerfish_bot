import logging
from datetime import datetime
from io import BytesIO
from textwrap import dedent
from unittest.mock import patch

import pytest
import telegram  # noqa https://youtrack.jetbrains.com/issue/PY-60059
from telegram.ext import ApplicationBuilder  # noqa

from run.telegram.bot import TelegramBot
from src.bot import BotState
from src.logger import BaseLogger


class FakeTelegramBot:
    def __init__(self):
        pass

    async def send_message(self, *args, **kwargs):
        pass


class FakeTelegramApp:
    def __init__(self):
        self.bot = FakeTelegramBot()

    def start_polling(self):
        pass

    def add_handler(self, *args, **kwargs):
        pass


class FakeTelegramFile:
    def __init__(self, content: str):
        self.content = content
        self.file_path = ""

    async def download_to_memory(self, file: BytesIO):
        file.write(bytearray(self.content, encoding="utf-8"))


@pytest.fixture
def app() -> FakeTelegramApp:
    return FakeTelegramApp()


def create_update(text: str | None = None, is_file: bool = False) -> telegram.Update:
    tg_user = telegram.User(username="local_user", id=42, first_name="local_user", is_bot=False)
    tg_chat = telegram.Chat(id=42, type="private")
    document = telegram.Document(file_id="f", file_unique_id="42") if is_file else None
    return telegram.Update(
        message=telegram.Message(
            text=text, document=document, chat=tg_chat, date=datetime.today(), message_id=42, from_user=tg_user,
        ),
        update_id=42,
    )


@pytest.mark.asyncio
async def test_telegram_bot(tmp_path, app):
    santa_info = dedent(
        """\
        local_user,chicken,dog
        local_user,dog
        """
    )

    with (
        patch.object(ApplicationBuilder, "build") as mock_app_build,
        patch.object(FakeTelegramBot, "send_message") as mock_send_message,
        patch.object(telegram.Document, "get_file") as mock_get_file,
    ):
        mock_app_build.side_effect = lambda: app
        mock_get_file.side_effect = [
            FakeTelegramFile(content=santa_info),
        ]
        updates = [
            create_update(text="/start"),
            create_update(text="/santa_init"),
            create_update(is_file=True),
            create_update(text="/santa_start gg"),
            create_update(text="/santa"),
            create_update(text="hahaha"),
        ]

        logger = BaseLogger(name="Bot")
        logger.set_level(logging.WARNING)
        tg_bot = TelegramBot(logger=logger, dir_path=tmp_path)

        with patch.object(tg_bot.bot.world, "is_admin") as mock_is_admin:
            mock_is_admin.side_effect = lambda _: True
            for update in updates:
                await tg_bot.handle_update(update, context=None)

    expected_output = [
        'Что тебе от меня надо, local_user',
        'Пришли текстовый файл с юзерами и запрещенными парами.',
        'Прочитал! 3 юзеров и 1 пар',
        "Перестановка сгенерирована! Успехов! seed: 'gg'",
        'Ты, local_user, даришь подарок @chicken! Такие дела.',
        'hahaha?',
    ]

    assert len(expected_output) == len(mock_send_message.mock_calls)
    for mock_call, expected_text in zip(mock_send_message.mock_calls, expected_output):
        reply_text = mock_call.kwargs["text"]
        assert reply_text == expected_text

    assert set(tg_bot.bot.santa_module.usernames) == {"local_user", "chicken", "dog"}
    assert tg_bot.bot.santa_module.forbidden_pairs == [("local_user", "dog")]
    assert tg_bot.bot.state == BotState.IDLE
