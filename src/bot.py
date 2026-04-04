import random
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from textwrap import dedent

from src.base_classes import Message, User
from src.file_manager import FileManager
from src.logger import Logger, BaseLogger
from src.modules import NGramTalkModule, SantaModule


class BotState(Enum):
    IDLE = 1
    LEARN_TEXT_WAITING_TEXT_ID = 2
    LEARN_TEXT_WAITING_TEXT = 3
    FORGET_TEXT_WAITING_TEXT_ID = 4
    HIDDEN_SANTA_WAITING_FILE = 5


@dataclass
class Reply:
    text: str | None = None
    sticker: str | None = None
    reaction: str | None = None


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
    NGRAM_MODULE_SAVE_FILE_NAME: str = "ngram_module_save_file.txt"
    DEFAULT_DIR_PATH: str = "./files"

    def __init__(self, world: World, dir_path: str | Path = DEFAULT_DIR_PATH, logger: Logger | None = None):
        if logger is None:
            logger = BaseLogger(name="Bot")
        self.logger: Logger = logger

        self.world: World = world

        self.state: BotState = BotState.IDLE  # later it should be state per user or group, now its just global

        self.file_manager = FileManager(dir_path=dir_path)

        self.ngram_talk_module: NGramTalkModule = NGramTalkModule(n=3)
        if self.file_manager.exists(Bot.NGRAM_MODULE_SAVE_FILE_NAME, tmp=False):
            with self.file_manager.open(Bot.NGRAM_MODULE_SAVE_FILE_NAME, tmp=False) as file:
                text = "\n".join(file.readlines())
            self.ngram_talk_module.deserialize_from_text(text)

        self.text_id: str = ""

        self.santa_module = SantaModule()

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
            else:
                random_reaction = random.choice(
                    [
                        "EYES",
                        "FACE_SCREAMING_IN_FEAR",
                        "FACE_WITH_ONE_EYEBROW_RAISED",
                        "FEARFUL_FACE",
                        "FIRE",
                        "HANDSHAKE",
                        "OK_HAND_SIGN",
                    ]
                )
                await self.world.reply(message, reply=Reply(reaction=random_reaction))

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

    async def handle_file(self, message: Message):
        self.logger.info(f"Got file {message.filepath} | {message.id}")
        if not message.filepath:
            return

        filepath = message.filepath

        if self.state == BotState.LEARN_TEXT_WAITING_TEXT:
            with self.file_manager.open(filepath, tmp=True) as file:
                self.ngram_talk_module.learn_text(self.text_id, '\n'.join(file.readlines()))

            await self._reply(message, reply=Reply(text=f'Текст сохранен как {self.text_id}'))

            with self.file_manager.open(Bot.NGRAM_MODULE_SAVE_FILE_NAME, tmp=False, mode="w") as file:
                file.write(self.ngram_talk_module.serialize_to_text())
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
        elif text.startswith("/forget_text"):
            if not self.world.is_admin(message.from_user):
                await self._reply(message, reply=Reply(text="У тебя нет полномочий для этого!"))
                return
            self.state = BotState.FORGET_TEXT_WAITING_TEXT_ID
            msg = dedent(
                f"""\
                Напиши название удаляемого текста. Возможные варианты:
                {' '.join(self.ngram_talk_module.counts_per_text.keys())}
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
            text = self.ngram_talk_module.handle_message(message)
            await self._reply(message, reply=Reply(text=text))
        elif self.state == BotState.LEARN_TEXT_WAITING_TEXT_ID:
            self.text_id = message.text.split("\n")[0]
            self.state = BotState.LEARN_TEXT_WAITING_TEXT
            await self._reply(message, reply=Reply(text=f'Пришли текстовый файл с текстом.'))
        elif self.state == BotState.FORGET_TEXT_WAITING_TEXT_ID:
            text_id = message.text.split("\n")[0]
            self.ngram_talk_module.forget_text(text_id)
            self.state = BotState.IDLE
            await self._reply(message, reply=Reply(text=f'Текст {text_id} удален'))
