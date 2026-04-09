from collections import defaultdict
from textwrap import dedent
from unittest.mock import patch

import pytest
from freezegun import freeze_time

from base_classes import Message, Chat, User, UserPrivileges
from src.bot import Reply, BotState, Bot, BotSettings


@pytest.mark.asyncio
async def test_use_reaction_if_empty_message(bot, user):
    bot.reactions = ["smiling"]
    message = Message(from_user=user)

    with patch.object(bot.world, "reply") as mock_reply:
        await bot.handle_message(message)

    mock_reply.assert_called_once_with(message=message, reply=Reply(reaction="smiling"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "text",
    [
        "/start",
        "hello",
        "/santa",
        "???",
        "/love",
        "/learn_text",
    ]
)
async def test_not_accept_messages_from_strangers(bot, user, text: str):
    user.privileges = UserPrivileges.UNKNOWN
    message = Message(text=f"{text}", from_user=user)
    initial_state = bot.state

    with (
        patch.object(bot.world, "reply") as mock_reply,
        patch.object(bot.world, "send_text_to_any_chat") as mock_send,
    ):
        await bot.handle_message(message)

    mock_reply.assert_called_once_with(message=message, reply=Reply(text="Я не знаю тебя!"))
    mock_send.assert_not_called()
    assert bot.state == initial_state


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method",
    [
        "send",
        "learn_text",
        "learn_swears",
        "forget_text",
        "santa_init",
        "santa_start",
    ]
)
async def test_commands_do_nothing_if_no_admin(bot, user, method: str):
    user.privileges = UserPrivileges.GUEST
    message = Message(text=f"/{method}", from_user=user)
    initial_state = bot.state

    with (
        patch.object(bot.world, "reply") as mock_reply,
        patch.object(bot.world, "send_text_to_any_chat") as mock_send,
    ):
        await bot.handle_message(message)

    mock_reply.assert_called_once_with(message=message, reply=Reply(text="У тебя нет полномочий для этого!"))
    mock_send.assert_not_called()
    assert bot.state == initial_state


@pytest.mark.asyncio
async def test_command_send(bot, user):
    message = Message(text="/send chat_id 42 omg", from_user=user)

    with patch.object(bot.world, "send_text_to_any_chat") as mock_send:
        await bot.handle_message(message)

    mock_send.assert_called_once_with(chat_id="chat_id", message_thread_id="42", text="omg")


@pytest.mark.asyncio
async def test_command_start(bot, user):
    message = Message(text="/start", from_user=user)

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message)

    mock_reply.assert_called_once()

    reply = mock_reply.mock_calls[0].kwargs["reply"]
    assert reply.text == "Что тебе от меня надо, DrillerName"
    assert reply.sticker is None
    assert reply.reaction is None


@pytest.mark.asyncio
async def test_command_learn_text(bot, user):
    message = Message(text="/learn_text", from_user=user)

    assert bot.state == BotState.IDLE

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message)

    mock_reply.assert_called_once_with(
        message=message,
        reply=Reply(text="Напиши название, под которым я запомню этот текст."),
    )

    assert bot.state == BotState.LEARN_TEXT_WAITING_TEXT_ID


@pytest.mark.asyncio
async def test_command_learn_swears(bot, user):
    message = Message(text="/learn_swears", from_user=user)

    assert bot.state == BotState.IDLE

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message)

    mock_reply.assert_called_once_with(
        message=message,
        reply=Reply(text="Пришли текстовый файл со словами."),
    )

    assert bot.state == BotState.LEARN_SWEARS_WAITING_TEXT


@pytest.mark.asyncio
async def test_command_forget_text(bot, user):
    message = Message(text="/forget_text", from_user=user)

    assert bot.state == BotState.IDLE

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message)

    expected_reply_text = "Напиши название удаляемого текста. Возможные варианты:\ntext_first text_second\n"

    mock_reply.assert_called_once_with(
        message=message,
        reply=Reply(text=expected_reply_text),
    )

    assert bot.state == BotState.FORGET_TEXT_WAITING_TEXT_ID


@pytest.mark.asyncio
async def test_command_santa_init(bot, user):
    message = Message(text="/santa_init", from_user=user)

    assert bot.state == BotState.IDLE

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message)

    expected_reply_text = "Пришли текстовый файл с юзерами и запрещенными парами."

    mock_reply.assert_called_once_with(
        message=message,
        reply=Reply(text=expected_reply_text),
    )

    assert bot.state == BotState.HIDDEN_SANTA_WAITING_FILE


@pytest.mark.asyncio
async def test_command_santa_start(bot, user):
    seed = "grunt"
    message = Message(text=f"/santa_start {seed}", from_user=user)

    bot.state = BotState.HIDDEN_SANTA_WAITING_FILE

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message)

    expected_reply_text = f"Перестановка сгенерирована! Успехов! seed: '{seed}'"

    mock_reply.assert_called_once_with(
        message=message,
        reply=Reply(text=expected_reply_text),
    )

    assert bot.santa_module.permutation["Driller"] == "Engineer"
    assert bot.state == BotState.IDLE


@pytest.mark.asyncio
async def test_command_santa(bot, user):
    message = Message(text=f"/santa", from_user=user)

    bot.state = BotState.HIDDEN_SANTA_WAITING_FILE
    bot.santa_module.generate_permutation()

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message)

    expected_reply_text = f"Ты, Driller, даришь подарок @Engineer! Такие дела."

    mock_reply.assert_called_once_with(
        message=message,
        reply=Reply(text=expected_reply_text),
    )

    assert bot.state == BotState.IDLE


@pytest.mark.asyncio
async def test_idle_talk(bot, user):
    message = Message(text="Engineer", from_user=user)

    assert bot.state == BotState.IDLE

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message)

    mock_reply.assert_called_once()
    reply = mock_reply.mock_calls[0].kwargs["reply"]

    assert "turret" in reply.text
    assert reply.sticker is None
    assert reply.reaction is None

    assert bot.state == BotState.IDLE


@pytest.mark.asyncio
async def test_learn_text_waiting_text_id(bot, user):
    bot.state = BotState.LEARN_TEXT_WAITING_TEXT_ID

    text_id = "Manual"
    message = Message(text=text_id, from_user=user)

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message)

    expected_reply_text = "Пришли текстовый файл с текстом."
    mock_reply.assert_called_once_with(message=message, reply=Reply(text=expected_reply_text))

    assert bot.text_id == text_id
    assert bot.state == BotState.LEARN_TEXT_WAITING_TEXT


@pytest.mark.asyncio
async def test_forget_text_waiting_text_id(bot, user):
    bot.state = BotState.FORGET_TEXT_WAITING_TEXT_ID

    text_id = "text_first"
    message = Message(text=text_id, from_user=user)

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message)

    expected_reply_text = f"Текст {text_id} удален"
    mock_reply.assert_called_once_with(message=message, reply=Reply(text=expected_reply_text))

    assert list(bot.talk_module.ngram_generator.counts_per_text.keys()) == ["text_second"]
    assert bot.state == BotState.IDLE


@pytest.mark.asyncio
async def test_file_learn_text_waiting_text(bot, user, tmp_path):
    bot.state = BotState.LEARN_TEXT_WAITING_TEXT
    text_id = "text_third"
    bot.text_id = text_id
    assert text_id not in bot.talk_module.ngram_generator.counts_per_text

    with open(tmp_path / "tmp" / "some_text.txt", "w", encoding="utf-8") as file:
        file.write("Cryo driller is nice")

    message = Message(filepath="some_text.txt", from_user=user)

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message)

    expected_reply_text = f"Текст сохранен как '{text_id}', 4 слов."
    mock_reply.assert_called_once_with(message=message, reply=Reply(text=expected_reply_text))

    assert text_id in bot.talk_module.ngram_generator.counts_per_text
    assert bot.state == BotState.IDLE


@pytest.mark.asyncio
async def test_file_learn_swears_waiting_text(bot, user, tmp_path):
    bot.state = BotState.LEARN_SWEARS_WAITING_TEXT

    with open(tmp_path / "tmp" / "some_text.txt", "w", encoding="utf-8") as file:
        file.write("chicken\ndog")

    message = Message(filepath="some_text.txt", from_user=user)

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message)

    expected_reply_text = f"Прочитано 2 слов!"
    mock_reply.assert_called_once_with(message=message, reply=Reply(text=expected_reply_text))

    assert ["chicken", "dog"] in bot.talk_module.swear_replacer.tag_to_swears.values()
    assert bot.state == BotState.IDLE


@pytest.mark.asyncio
async def test_file_hidden_santa_waiting_file(bot, user, tmp_path):
    bot.state = BotState.HIDDEN_SANTA_WAITING_FILE
    santa_info = dedent(
        """\
        Grunt,Mactera,Spitballer
        Grunt,Mactera
        """
    )

    with open(tmp_path / "tmp" / "some_text.txt", "w", encoding="utf-8") as file:
        file.write(santa_info)

    message = Message(filepath="some_text.txt", from_user=user)

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message)

    expected_reply_text = f"Прочитал! 3 юзеров и 1 пар"
    mock_reply.assert_called_once_with(message=message, reply=Reply(text=expected_reply_text))

    assert set(bot.santa_module.usernames) == {"Grunt", "Mactera", "Spitballer"}
    assert bot.santa_module.forbidden_pairs == [("Grunt", "Mactera")]
    assert bot.state == BotState.IDLE


@pytest.mark.asyncio
async def test_file_is_not_expected(bot, user):
    bot.state = BotState.IDLE
    message = Message(filepath="some_text.txt", from_user=user)

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message)

    expected_reply_text = "Не ожидаю файл... мне пофиг на него"
    mock_reply.assert_called_once_with(message=message, reply=Reply(text=expected_reply_text))

    assert bot.state == BotState.IDLE


@pytest.mark.asyncio
async def test_talk_module(bot, user, tmp_path):
    with open(tmp_path / "tmp" / "swears.txt", "w", encoding="utf-8") as file:
        file.write("курица\nелку")

    with open(tmp_path / "tmp" / "ngrams.txt", "w", encoding="utf-8") as file:
        file.write("собака упала на улицу")

    bot.talk_module.swear_replacer.chance_to_replace = 1.0
    bot.talk_module.swear_replacer.short_swear_relative_chance = None

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(Message(text="/learn_swears", from_user=user))
        await bot.handle_message(Message(filepath="swears.txt", from_user=user))
        await bot.handle_message(Message(text="/learn_text", from_user=user))
        await bot.handle_message(Message(text="first", from_user=user))
        await bot.handle_message(Message(filepath="ngrams.txt", from_user=user))
        await bot.handle_message(Message(text="собака", from_user=user))

    assert len(mock_reply.mock_calls) == 6

    mock_call_last = mock_reply.mock_calls[-1]
    reply_text = mock_call_last.kwargs["reply"].text
    expected_reply_text = f"Собака упала на елку?"
    assert reply_text == expected_reply_text

    assert bot.state == BotState.IDLE

    # checking that loading from files working
    new_bot = Bot(world=bot.world, dir_path=tmp_path)
    assert new_bot.talk_module.swear_replacer.tag_to_swears.keys() == bot.talk_module.swear_replacer.tag_to_swears.keys()
    assert new_bot.talk_module.ngram_generator.counts_per_text.keys() == bot.talk_module.ngram_generator.counts_per_text.keys()


@pytest.mark.asyncio
async def test_text_case_changer(bot, user):
    bot.text_case_changer.chance_random_case = 0.25
    bot.text_case_changer.chance_upper_case = 0.35
    bot.text_case_changer.random_case_max_len = 100

    txt = "a" * 100

    n = 1000
    results = defaultdict(int)
    with (patch.object(bot.world, "reply") as mock_reply):
        for _ in range(n):
            await bot.handle_message(Message(text=txt, from_user=user))

    for mock_call in mock_reply.mock_calls:
        reply_txt = mock_call.kwargs["reply"].text
        reply_txt = reply_txt[1:]

        if "a" in reply_txt and "A" in reply_txt:
            results["random"] += 1
        elif "a" in reply_txt:
            results["default"] += 1
        elif "A" in reply_txt:
            results["upper"] += 1

    assert len(mock_reply.mock_calls) == n
    assert results["default"] + results["random"] + results["upper"] == n
    assert abs(results["default"] / n - 0.4) < 0.1
    assert abs(results["random"] / n - 0.25) < 0.05
    assert abs(results["upper"] / n - 0.35) < 0.05


@pytest.mark.asyncio
async def test_send_stickers(bot, user):
    bot.stickers = ["sticker_with_cat"]
    bot.chance_send_sticker = 1.0

    with (patch.object(bot.world, "reply") as mock_reply):
        await bot.handle_message(message=Message(sticker="omg_sticker", from_user=user))
        await bot.handle_message(message=Message(text="A", from_user=user))

    assert len(mock_reply.mock_calls) == 3

    assert mock_reply.mock_calls[0].kwargs["reply"] == Reply(sticker="sticker_with_cat")
    assert mock_reply.mock_calls[2].kwargs["reply"] == Reply(sticker="sticker_with_cat")


@pytest.mark.asyncio
async def test_command_horoscope(bot, user):
    message = Message(text=f"/horoscope", from_user=user)

    n = 100
    with patch.object(bot.world, "reply") as mock_reply, freeze_time("2026-04-08"):
        for _ in range(n):
            await bot.handle_message(message)

    assert len(mock_reply.mock_calls) == n
    results = {call.kwargs["reply"].text for call in mock_reply.mock_calls}
    assert len(results) == 1

    expected_reply_text = (
        "DrillerName, пришло время взяться за сложную задачу! "
        "Сегодня тебя ждет успех в ней. "
        "Ты победишь в какой-нибудь игре, но стоит вовремя остановиться! Сегодня твой интеллект в норме. "
        "Сегодняшние новости могут оказаться не очень хорошими, берегись! "
        "Лучше надеть что-то потемнее, в этом ты будешь выглядеть потрясающе! "
    )
    assert results.pop() == expected_reply_text

    assert bot.state == BotState.IDLE


@pytest.mark.asyncio
async def test_command_love(bot, user):
    message = Message(
        text=f"/love",
        chat=Chat(users=[User(username="first", name="FirstName"), User(username="second", name="SecondName")]),
        from_user=user,
    )

    n = 100
    with patch.object(bot.world, "reply") as mock_reply, freeze_time("2026-04-08"):
        for _ in range(n):
            await bot.handle_message(message)

    assert len(mock_reply.mock_calls) == n
    results = {call.kwargs["reply"].text for call in mock_reply.mock_calls}
    assert len(results) == 1

    expected_reply_text = "Сегодня я люблю FirstName и недолюбливаю SecondName"
    assert results.pop() == expected_reply_text

    assert bot.state == BotState.IDLE


@pytest.mark.asyncio
async def test_command_choose(bot, user):
    message = Message(text="/choose Как совунья размножается: откладывает яйца или жахается?", from_user=user)

    with patch.object(bot.world, "reply") as mock_reply:
        await bot.handle_message(message)

    assert len(mock_reply.mock_calls) == 1
    result = mock_reply.mock_calls[0].kwargs["reply"].text

    assert result.split("\n")[0] == "Я утверждаю, что жахается!"
    assert "откладывает яйца" in ''.join(result.split("\n")[1:]).lower()

    assert bot.state == BotState.IDLE


@pytest.mark.asyncio
async def test_bot_settings(world, tmp_path):
    settings_str = dedent(
        """\
        {
            "stickers": [
                "omg_sticker",
                "omg_sticker2"
            ],
            "reactions": [
                "omg_reaction",
                "omg_reaction2"
            ],
            "chance_talk_send_sticker": 0.2,
            "chance_talk_random_case": 0.1,
            "chance_talk_upper_case": 0.1,
            "chance_talk_replace_to_swear": 0.2,
            
            "talk_n_key_words": 7,
            "talk_n_words_in_sentence": 18,
            "chance_talk_new_line_after_sentence": 0.3,
            
            "short_swear_max_length": 7,
            "short_swear_relative_chance": 0.8,
            
            "ngram_generator_n": 5
        }
        """
    )
    bot = Bot(world=world, dir_path=tmp_path, bot_settings=BotSettings.from_str(settings_str))

    assert bot.stickers == ["omg_sticker", "omg_sticker2"]
    assert bot.reactions == ["omg_reaction", "omg_reaction2"]

    assert bot.chance_send_sticker == 0.2
    assert bot.text_case_changer.chance_random_case == 0.1
    assert bot.text_case_changer.chance_upper_case == 0.1

    assert bot.talk_module.swear_replacer.chance_to_replace == 0.2
    assert bot.talk_module.swear_replacer.short_swear_max_len == 7
    assert bot.talk_module.swear_replacer.short_swear_relative_chance == 0.8
    assert bot.talk_module.ngram_generator.n == 5

    assert bot.talk_module.n_key_words == 7
    assert bot.talk_module.n_words_in_sentence == 18
    assert bot.talk_module.chance_new_line_after_sentence == 0.3
