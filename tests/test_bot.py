import pytest
from unittest.mock import patch
from textwrap import dedent

from base_classes import Message
from src.bot import Reply, BotState


NO_PERMISSION_TEXT = "У тебя нет полномочий для этого!"


def test_use_reaction_if_no_file_no_text(bot):
    message = Message()

    with patch.object(bot.world, "reply") as mock_reply:
        bot.handle_message(message)

    mock_reply.assert_called_once()

    reply = mock_reply.mock_calls[0].kwargs["reply"]
    assert reply.text is None
    assert reply.sticker is None
    assert reply.reaction is not None


@pytest.mark.parametrize(
    "method",
    [
        "send",
        "learn_text",
        "forget_text",
        "santa_init",
        "santa_start",
    ]
)
def test_commands_do_nothing_if_no_admin(bot, method: str):
    message = Message(text=f"/{method}")
    initial_state = bot.state

    with (
        patch.object(bot.world, "reply") as mock_reply,
        patch.object(bot.world, "is_admin") as mock_is_admin,
        patch.object(bot.world, "send_text_to_any_chat") as mock_send,
    ):
        mock_is_admin.side_effect = lambda _: False
        bot.handle_message(message)

    mock_is_admin.assert_called_once()
    mock_reply.assert_called_once_with(message=message, reply=Reply(text=NO_PERMISSION_TEXT))
    mock_send.assert_not_called()
    assert bot.state == initial_state


def test_command_send(bot):
    message = Message(text="/send chat_id 42 omg")

    with patch.object(bot.world, "send_text_to_any_chat") as mock_send:
        bot.handle_message(message)

    mock_send.assert_called_once_with(chat_id="chat_id", message_thread_id="42", text="omg")


def test_command_start(bot, user):
    message = Message(text="/start", from_user=user)

    with (patch.object(bot.world, "reply") as mock_reply):
        bot.handle_message(message)

    mock_reply.assert_called_once()

    reply = mock_reply.mock_calls[0].kwargs["reply"]
    assert user.username in reply.text
    assert reply.sticker is None
    assert reply.reaction is None


def test_command_learn_text(bot):
    message = Message(text="/learn_text")

    assert bot.state == BotState.IDLE

    with (patch.object(bot.world, "reply") as mock_reply):
        bot.handle_message(message)

    mock_reply.assert_called_once_with(
        message=message,
        reply=Reply(text="Напиши название, под которым я запомню этот текст."),
    )

    assert bot.state == BotState.LEARN_TEXT_WAITING_TEXT_ID


def test_command_forget_text(bot):
    message = Message(text="/forget_text")

    assert bot.state == BotState.IDLE

    with (patch.object(bot.world, "reply") as mock_reply):
        bot.handle_message(message)

    expected_reply_text = "Напиши название удаляемого текста. Возможные варианты:\ntext_first text_second\n"

    mock_reply.assert_called_once_with(
        message=message,
        reply=Reply(text=expected_reply_text),
    )

    assert bot.state == BotState.FORGET_TEXT_WAITING_TEXT_ID


def test_command_santa_init(bot):
    message = Message(text="/santa_init")

    assert bot.state == BotState.IDLE

    with (patch.object(bot.world, "reply") as mock_reply):
        bot.handle_message(message)

    expected_reply_text = "Пришли текстовый файл с юзерами и запрещенными парами."

    mock_reply.assert_called_once_with(
        message=message,
        reply=Reply(text=expected_reply_text),
    )

    assert bot.state == BotState.HIDDEN_SANTA_WAITING_FILE


def test_command_santa_start(bot):
    seed = "grunt"
    message = Message(text=f"/santa_start {seed}")

    bot.state = BotState.HIDDEN_SANTA_WAITING_FILE

    with (patch.object(bot.world, "reply") as mock_reply):
        bot.handle_message(message)

    expected_reply_text = f"Перестановка сгенерирована! Успехов! seed: '{seed}'"

    mock_reply.assert_called_once_with(
        message=message,
        reply=Reply(text=expected_reply_text),
    )

    assert bot.santa_module.permutation["Driller"] == "Engineer"
    assert bot.state == BotState.IDLE


def test_command_santa(bot, user):
    message = Message(text=f"/santa", from_user=user)

    bot.state = BotState.HIDDEN_SANTA_WAITING_FILE
    bot.santa_module.generate_permutation()

    with (patch.object(bot.world, "reply") as mock_reply):
        bot.handle_message(message)

    expected_reply_text = f"Ты, Driller, даришь подарок @Engineer! Такие дела."

    mock_reply.assert_called_once_with(
        message=message,
        reply=Reply(text=expected_reply_text),
    )

    assert bot.state == BotState.IDLE


def test_idle_talk(bot):
    message = Message(text="Engineer")

    assert bot.state == BotState.IDLE

    with (patch.object(bot.world, "reply") as mock_reply):
        bot.handle_message(message)

    mock_reply.assert_called_once()
    reply = mock_reply.mock_calls[0].kwargs["reply"]

    assert "turret" in reply.text
    assert reply.sticker is None
    assert reply.reaction is None

    assert bot.state == BotState.IDLE


def test_learn_text_waiting_text_id(bot):
    bot.state = BotState.LEARN_TEXT_WAITING_TEXT_ID

    text_id = "Manual"
    message = Message(text=text_id)

    with (patch.object(bot.world, "reply") as mock_reply):
        bot.handle_message(message)

    expected_reply_text = "Пришли текстовый файл с текстом."
    mock_reply.assert_called_once_with(message=message, reply=Reply(text=expected_reply_text))

    assert bot.text_id == text_id
    assert bot.state == BotState.LEARN_TEXT_WAITING_TEXT


def test_forget_text_waiting_text_id(bot):
    bot.state = BotState.FORGET_TEXT_WAITING_TEXT_ID

    text_id = "text_first"
    message = Message(text=text_id)

    with (patch.object(bot.world, "reply") as mock_reply):
        bot.handle_message(message)

    expected_reply_text = f"Текст {text_id} удален"
    mock_reply.assert_called_once_with(message=message, reply=Reply(text=expected_reply_text))

    assert list(bot.ngram_talk_module.counts_per_text.keys()) == ["text_second"]
    assert bot.state == BotState.IDLE


def test_file_learn_text_waiting_text(bot, tmp_path):
    bot.state = BotState.LEARN_TEXT_WAITING_TEXT
    text_id = "text_third"
    bot.text_id = text_id
    assert text_id not in bot.ngram_talk_module.counts_per_text

    with open(tmp_path / "some_text.txt", "w", encoding="utf-8") as file:
        file.write("Cryo driller is nice")

    message = Message(filepath="some_text.txt")

    with (patch.object(bot.world, "reply") as mock_reply):
        bot.handle_message(message)

    expected_reply_text = f"Текст сохранен как {text_id}"
    mock_reply.assert_called_once_with(message=message, reply=Reply(text=expected_reply_text))

    assert text_id in bot.ngram_talk_module.counts_per_text
    assert bot.state == BotState.IDLE


def test_file_hidden_santa_waiting_file(bot, tmp_path):
    bot.state = BotState.HIDDEN_SANTA_WAITING_FILE
    santa_info = dedent(
        """\
        Grunt,Mactera,Spitballer
        Grunt,Mactera
        """
    )

    with open(tmp_path / "some_text.txt", "w", encoding="utf-8") as file:
        file.write(santa_info)

    message = Message(filepath="some_text.txt")

    with (patch.object(bot.world, "reply") as mock_reply):
        bot.handle_message(message)

    expected_reply_text = f"Прочитал! 3 юзеров и 1 пар"
    mock_reply.assert_called_once_with(message=message, reply=Reply(text=expected_reply_text))

    assert set(bot.santa_module.usernames) == {"Grunt", "Mactera", "Spitballer"}
    assert bot.santa_module.forbidden_pairs == [("Grunt", "Mactera")]
    assert bot.state == BotState.IDLE


def test_file_is_not_expected(bot):
    bot.state = BotState.IDLE
    message = Message(filepath="some_text.txt")

    with (patch.object(bot.world, "reply") as mock_reply):
        bot.handle_message(message)

    expected_reply_text = "Не ожидаю файл... мне пофиг на него"
    mock_reply.assert_called_once_with(message=message, reply=Reply(text=expected_reply_text))

    assert bot.state == BotState.IDLE
