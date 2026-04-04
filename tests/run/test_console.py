import pytest
from unittest.mock import patch
from textwrap import dedent

from run.console.bot import run
from src.bot import BotState


def test_console_bot(bot, tmp_path):
    santa_info = dedent(
        """\
        local_user,chicken,dog
        local_user,dog
        """
    )
    with open(tmp_path / "tmp" / "santa.txt", "w", encoding="utf-8") as file:
        file.write(santa_info)

    with patch("builtins.input") as patched_input, patch.object(bot.world, "reply") as patched_reply:
        patched_input.side_effect = [
            "/start",
            "/santa_init",
            "/file santa.txt",
            "/santa_start gg",
            "/santa",
            "hahaha",
            KeyboardInterrupt(),
        ]
        run(bot)

    expected_output = [
        'Что тебе от меня надо, local_user',
        'Пришли текстовый файл с юзерами и запрещенными парами.',
        'Прочитал! 3 юзеров и 1 пар',
        "Перестановка сгенерирована! Успехов! seed: 'gg'",
        'Ты, local_user, даришь подарок @chicken! Такие дела.',
        'Hahaha.',
    ]

    assert len(expected_output) == len(patched_reply.mock_calls)
    for mock_call, expected_text in zip(patched_reply.mock_calls, expected_output):
        reply_text = mock_call.kwargs["reply"].text
        assert reply_text == expected_text

    assert set(bot.santa_module.usernames) == {"local_user", "chicken", "dog"}
    assert bot.santa_module.forbidden_pairs == [("local_user", "dog")]
    assert bot.state == BotState.IDLE
