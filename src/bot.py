import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from textwrap import dedent
import json

from src.base_classes import Message, User
from src.file_manager import FileManager
from src.logger import Logger, BaseLogger
from src.modules import TalkModule, SwearReplacer, NGramGenerator, SantaModule
from src.modules.talk.base import tokenize


class BotState(Enum):
    IDLE = 1
    LEARN_TEXT_WAITING_TEXT_ID = 2
    LEARN_TEXT_WAITING_TEXT = 3
    FORGET_TEXT_WAITING_TEXT_ID = 4
    HIDDEN_SANTA_WAITING_FILE = 5
    LEARN_SWEARS_WAITING_TEXT = 6


@dataclass
class Reply:
    text: str | None = None
    sticker: str | None = None
    reaction: str | None = None


class TextCaseChanger:
    def __init__(self, chance_random_case: float, chance_upper_case: float):
        self.chance_random_case = chance_random_case
        self.chance_upper_case = chance_upper_case

    def process_text(self, text: str):
        text_case = random.choices(
            ["normal", "upper", "random"],
            weights=[
                1 - self.chance_random_case - self.chance_upper_case,
                self.chance_upper_case,
                self.chance_random_case,
            ],
        )[0]
        if text_case == "upper":
            text = text.upper()
        elif text_case == "random":
            max_len = 30
            if "." in text and len(text.split(".")[0]) < max_len:
                first_part, second_part = text.split(".", maxsplit=1)
            else:
                first_part, second_part = text[:max_len], text[max_len:]
            text = ''.join([ch.upper() if random.random() < 0.5 else ch.lower() for ch in first_part]) + second_part

        return text


@dataclass
class BotSettings:
    stickers: list[str] = field(default_factory=lambda: [])
    reactions: list[str] = field(default_factory=lambda: [])

    chance_talk_send_sticker: float = 0.0
    chance_talk_random_case: float = 0.0
    chance_talk_upper_case: float = 0.0
    chance_talk_replace_to_swear: float = 0.0

    talk_n_key_words: int = 5
    talk_n_words_in_sentence: int = 25
    chance_talk_new_line_after_sentence: float = 0.0

    short_swear_max_length: int = 7
    short_swear_relative_chance: float = 1.0

    ngram_generator_n: int = 3

    @staticmethod
    def from_str(text: str) -> "BotSettings":
        settings_dict = json.loads(text)
        settings = BotSettings()

        settings.stickers = settings_dict["stickers"]
        settings.reactions = settings_dict["reactions"]

        settings.chance_talk_send_sticker = settings_dict["chance_talk_send_sticker"]
        settings.chance_talk_random_case = settings_dict["chance_talk_random_case"]
        settings.chance_talk_upper_case = settings_dict["chance_talk_upper_case"]
        settings.chance_talk_replace_to_swear = settings_dict["chance_talk_replace_to_swear"]

        settings.talk_n_key_words = settings_dict["talk_n_key_words"]
        settings.n_words_in_sentence = settings_dict["n_words_in_sentence"]
        settings.chance_talk_new_line_after_sentence = settings_dict["chance_talk_new_line_after_sentence"]

        settings.short_swear_max_length = settings_dict["short_swear_max_length"]
        settings.short_swear_relative_chance = settings_dict["short_swear_relative_chance"]

        settings.ngram_generator_n = settings_dict["ngram_generator_n"]

        return settings


class World:
    def __init__(self):
        pass

    async def reply(self, message: Message, reply: Reply):
        raise NotImplementedError

    async def send_text_to_any_chat(self, text: str, chat_id: str, message_thread_id: str = None):
        raise NotImplementedError

    def is_admin(self, user: User) -> bool:
        raise NotImplementedError


class Bot:
    NGRAM_SAVE_FILE_NAME: str = "ngram_save_file.txt"
    SWEARS_SAVE_FILE_NAME: str = "swears_save_file.txt"
    DEFAULT_DIR_PATH: str = "./files"

    def __init__(
        self,
        world: World, dir_path: str | Path = DEFAULT_DIR_PATH,
        logger: Logger | None = None,
        bot_settings: BotSettings | None = None,
    ):
        settings: BotSettings = BotSettings() if bot_settings is None else bot_settings

        if logger is None:
            logger = BaseLogger(name="Bot")
        self.logger: Logger = logger

        self.world: World = world

        self.state: BotState = BotState.IDLE  # later it should be state per user or group, now its just global

        self.file_manager = FileManager(dir_path=dir_path)

        ngram_generator = NGramGenerator(n=settings.ngram_generator_n)
        if self.file_manager.exists(Bot.NGRAM_SAVE_FILE_NAME, tmp=False):
            with self.file_manager.open(Bot.NGRAM_SAVE_FILE_NAME, tmp=False) as file:
                text = "\n".join(file.readlines())
            ngram_generator = NGramGenerator.deserialize_from_text(text)
            self.logger.info("NGram save file found, ignoring 'ngram_generator_n' from config")

        swear_replacer = SwearReplacer(
            chance_to_replace=settings.chance_talk_replace_to_swear,
            short_swear_max_len=settings.short_swear_max_length,
            short_swear_relative_chance=settings.short_swear_relative_chance,
        )
        if self.file_manager.exists(Bot.SWEARS_SAVE_FILE_NAME, tmp=False):
            with self.file_manager.open(Bot.SWEARS_SAVE_FILE_NAME, tmp=False) as file:
                text = "\n".join(file.readlines())
            swear_replacer = SwearReplacer.deserialize_from_text(text)
            self.logger.info("Swear save file found, ignoring 'short_swear_max_length' from config")

            swear_replacer.chance_to_replace = settings.chance_talk_replace_to_swear
            swear_replacer.short_swear_relative_chance = settings.short_swear_relative_chance

        self.talk_module: TalkModule = TalkModule(
            ngram_generator=ngram_generator,
            swear_replacer=swear_replacer,
            n_key_words=settings.talk_n_key_words,
            n_words_in_sentence=settings.talk_n_words_in_sentence,
            chance_new_line_after_sentence=settings.chance_talk_new_line_after_sentence,
        )

        self.text_id: str = ""

        self.santa_module = SantaModule()

        self.chance_send_sticker: float = settings.chance_talk_send_sticker

        self.text_case_changer = TextCaseChanger(
            chance_random_case=settings.chance_talk_random_case,
            chance_upper_case=settings.chance_talk_upper_case,
        )

        self.stickers: list[str] = settings.stickers or [None]
        self.reactions: list[str] = settings.reactions or [None]

    def exit(self):
        """Cleaning up tmp files before turning off"""
        self.logger.info("Shutdown!")
        self.file_manager.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit()

    async def _reply(self, message: Message, reply: Reply, hide_reply: bool = False):
        user_str = message.from_user.username
        chat_str = (
            (message.chat.type or '') + ' ' + (message.chat.title or '') + ' ' + (str(message.chat.id) or '')
            + ' ' + (str(message.message_thread_id) or '')
        )
        content_for_log = "<hidden>" if hide_reply else (reply.text or reply.sticker or reply.reaction)
        self.logger.info(f"Replying to user {user_str} in chat {chat_str}: '{content_for_log}' | {message.id}")
        await self.world.reply(message=message, reply=reply)

    async def _send_text_to_any_chat(self, text: str, chat_id: str, message_thread_id: str = None):
        self.logger.info(f"Sending message to chat {chat_id}: '{text}' | {message_thread_id}")
        await self.world.send_text_to_any_chat(text=text, chat_id=chat_id, message_thread_id=message_thread_id)

    async def handle_message(self, message: Message):
        user_str = message.from_user.username
        chat_str = (message.chat.type or '') + (message.chat.title or '')
        self.logger.info(f"Got message from user {user_str} in chat {chat_str} | {message.id}")

        try:
            if message.filepath:
                await self.handle_file(message)
            elif message.text:
                await self.handle_text(message)
            elif message.sticker:
                await self.handle_sticker(message)
            else:
                await self.world.reply(message=message, reply=Reply(reaction=random.choice(self.reactions)))

        except Exception as e:
            err_msg = '\n'.join([str(a) for a in e.args])
            self.logger.warning(err_msg)
            reply_text = random.choice(
                [
                    "Ошибка!",
                    "Ошибка тупая",
                    "Я ошибся!",
                    "Проблемка",
                ]
            )
            await self._reply(message, Reply(text=reply_text))

    async def handle_sticker(self, message: Message):
        self.logger.info(f"Got sticker '{message.sticker}' | {message.id}")
        reply_sticker = random.choice(self.stickers)
        await self._reply(message=message, reply=Reply(sticker=reply_sticker))

    async def handle_file(self, message: Message):
        self.logger.info(f"Got file {message.filepath} | {message.id}")
        if not message.filepath:
            return

        filepath = message.filepath

        if self.state == BotState.LEARN_TEXT_WAITING_TEXT:
            with self.file_manager.open(filepath, tmp=True) as file:
                words = tokenize(' '.join(file.readlines()))
            self.talk_module.ngram_generator.learn_text(self.text_id, words)

            await self._reply(message, reply=Reply(text=f"Текст сохранен как '{self.text_id}', {len(words)} слов."))

            with self.file_manager.open(Bot.NGRAM_SAVE_FILE_NAME, tmp=False, mode="w") as file:
                file.write(self.talk_module.ngram_generator.serialize_to_text())
            self.state = BotState.IDLE

        elif self.state == BotState.LEARN_SWEARS_WAITING_TEXT:
            with self.file_manager.open(filepath, tmp=True) as file:
                words = [line.strip() for line in file.readlines() if ' ' not in line]
            self.talk_module.swear_replacer.learn_from_list(words)

            n_words = sum([len(ws) for ws in self.talk_module.swear_replacer.tag_to_swears.values()])
            await self._reply(message, reply=Reply(text=f'Прочитано {n_words} слов!'))

            with self.file_manager.open(Bot.SWEARS_SAVE_FILE_NAME, tmp=False, mode="w") as file:
                file.write(self.talk_module.swear_replacer.serialize_to_text())
            self.state = BotState.IDLE

        elif self.state == BotState.HIDDEN_SANTA_WAITING_FILE:
            with self.file_manager.open(filepath, tmp=True) as file:
                self.santa_module.initialize_from_str('\n'.join(file.readlines()))

            reply_txt = (
                f'Прочитал! {len(self.santa_module.usernames)} юзеров и {len(self.santa_module.forbidden_pairs)} пар'
            )
            await self._reply(message, reply=Reply(text=reply_txt))
            self.state = BotState.IDLE
        else:
            await self._reply(message, reply=Reply(text="Не ожидаю файл... мне пофиг на него"))

    async def handle_text(self, message: Message):
        text = message.text
        self.logger.info(f"Message text: '{text}' | {message.id}")
        # some commands are independent of current state
        if text.startswith("/send"):
            if not self.world.is_admin(message.from_user):
                await self._reply(message, reply=Reply(text="У тебя нет полномочий для этого!"))
                return

            _, chat_id, message_thread_id, text = text.split(maxsplit=3)
            await self._send_text_to_any_chat(chat_id=chat_id, message_thread_id=message_thread_id, text=text)
            return
        elif text.startswith("/start"):
            await self._reply(message, reply=Reply(text=f'Что тебе от меня надо, {message.from_user.username}'))
            self.state = BotState.IDLE
            return
        elif text.startswith("/learn_text"):
            if not self.world.is_admin(message.from_user):
                await self._reply(message, reply=Reply(text="У тебя нет полномочий для этого!"))
                return
            self.state = BotState.LEARN_TEXT_WAITING_TEXT_ID
            await self._reply(message, reply=Reply(text=f'Напиши название, под которым я запомню этот текст.'))
            return
        elif text.startswith("/learn_swears"):
            if not self.world.is_admin(message.from_user):
                await self._reply(message, reply=Reply(text="У тебя нет полномочий для этого!"))
                return
            self.state = BotState.LEARN_SWEARS_WAITING_TEXT
            await self._reply(message, reply=Reply(text=f'Пришли текстовый файл со словами.'))
            return
        elif text.startswith("/forget_text"):
            if not self.world.is_admin(message.from_user):
                await self._reply(message, reply=Reply(text="У тебя нет полномочий для этого!"))
                return
            self.state = BotState.FORGET_TEXT_WAITING_TEXT_ID
            msg = dedent(
                f"""\
                Напиши название удаляемого текста. Возможные варианты:
                {' '.join(self.talk_module.ngram_generator.counts_per_text.keys())}
                """
            )
            await self._reply(message, reply=Reply(text=msg))
            return
        elif text.startswith("/santa_init"):
            if not self.world.is_admin(message.from_user):
                await self._reply(message, reply=Reply(text="У тебя нет полномочий для этого!"))
                return
            self.state = BotState.HIDDEN_SANTA_WAITING_FILE
            await self._reply(message, reply=Reply(text=f'Пришли текстовый файл с юзерами и запрещенными парами.'))
            return
        elif text.startswith("/santa_start"):
            if not self.world.is_admin(message.from_user):
                await self._reply(message, reply=Reply(text="У тебя нет полномочий для этого!"))
                return
            seed = text.split(maxsplit=1)[1].strip() if len(text.split()) >= 2 else None
            self.santa_module.generate_permutation(seed)
            await self._reply(message, reply=Reply(text=f"Перестановка сгенерирована! Успехов! seed: '{seed}'"))
            self.state = BotState.IDLE
            return
        elif text.startswith("/santa"):
            text = self.santa_module.handle_message(message)
            await self._reply(message, reply=Reply(text=text), hide_reply=True)
            self.state = BotState.IDLE
            return

        if self.state == BotState.IDLE:
            text = self.talk_module.handle_message(message)
            text = self.text_case_changer.process_text(text)
            await self._reply(message, reply=Reply(text=text))

            if random.random() < self.chance_send_sticker:
                await self._reply(message, reply=Reply(sticker=random.choice(self.stickers)))
        elif self.state == BotState.LEARN_TEXT_WAITING_TEXT_ID:
            self.text_id = message.text.split("\n")[0]
            self.state = BotState.LEARN_TEXT_WAITING_TEXT
            await self._reply(message, reply=Reply(text=f'Пришли текстовый файл с текстом.'))
        elif self.state == BotState.FORGET_TEXT_WAITING_TEXT_ID:
            text_id = message.text.split("\n")[0]
            self.talk_module.ngram_generator.forget_text(text_id)
            self.state = BotState.IDLE
            await self._reply(message, reply=Reply(text=f'Текст {text_id} удален'))
