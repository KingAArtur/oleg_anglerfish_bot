import os
import random
from enum import Enum
from textwrap import dedent
from dataclasses import dataclass
from pathlib import Path

from src.base_classes import Message, User
from src.logger import Logger, BaseLogger

from modules import NGramTalkModule, SantaModule


class BotState(Enum):
    IDLE = 1
    LEARN_TEXT_WAITING_TEXT_ID = 2
    LEARN_TEXT_WAITING_TEXT = 3
    FORGET_TEXT_WAITING_TEXT_ID = 4
    HIDDEN_SANTA_WAITING_FILE = 5


class FileManager:
    def __init__(self, dir_path: str | Path):
        if isinstance(dir_path, str):
            dir_path = Path(dir_path)

        if not dir_path.exists():
            dir_path.mkdir()

        if dir_path.is_file():
            raise FileExistsError(p)

        self.dir_path: Path = dir_path

    def __call__(self, file_name: str) -> Path:
        return self.dir_path / file_name


@dataclass
class Reply:
    text: str | None = None
    sticker: str | None = None
    reaction: str | None = None


class World:
    def __init__(self):
        pass

    def reply(self, message: Message, reply: Reply):
        raise NotImplementedError

    def send_text_to_any_chat(self, text: str, chat_id: str, message_thread_id: str = None):
        raise NotImplementedError

    def is_admin(self, user: User) -> bool:
        raise NotImplementedError


class Bot:
    TMP_TEXT_FILE_NAME: str = "tmp.txt"
    NGRAM_MODULE_SAVE_FILE_NAME: str = "ngram_module_save_file.txt"

    def __init__(self, dir_path: str | Path = "./files", logger: Logger | None = None, world: World | None = None):
        if logger is None:
            logger = BaseLogger(name="Bot")
        self.logger: Logger = logger

        if world is None:
            world = World()
        self.world: World = world

        self.state: BotState = BotState.IDLE  # later it should be state per user or group, now its just global

        self.file_manager = FileManager(dir_path=dir_path)

        self.ngram_talk_module: NGramTalkModule = NGramTalkModule(n=3)
        if os.path.exists(self.file_manager(self.NGRAM_MODULE_SAVE_FILE_NAME)):
            with open(self.file_manager(self.NGRAM_MODULE_SAVE_FILE_NAME), encoding="utf-8") as file:
                text = "\n".join(file.readlines())
            self.ngram_talk_module.deserialize_from_text(text)
        self.text_id: str = ""

        self.santa_module = SantaModule()

    def exit(self):
        """Saving some state before turning off"""
        self.logger.info("Shutdown!")
        if os.path.exists(self.file_manager(self.TMP_TEXT_FILE_NAME)):
            os.remove(self.file_manager(self.TMP_TEXT_FILE_NAME))

        ngram_module_serialized = self.ngram_talk_module.serialize_to_text()
        with open(self.file_manager(self.NGRAM_MODULE_SAVE_FILE_NAME), "w", encoding="utf-8") as file:
            file.write(ngram_module_serialized)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit()

    def _reply(self, message: Message, reply: Reply, hide_text: bool = False):
        user_str = message.from_user.username
        chat_str = (
            (message.chat.type or '') + ' ' + (message.chat.title or '') + ' ' + (str(message.chat.id) or '')
            + ' ' + (str(message.message_thread_id) or '')
        )
        text_for_log = "<hidden>" if hide_text and reply.text is not None else reply.text
        self.logger.info(f"Replying to user {user_str} in chat {chat_str}: '{text_for_log or reply.sticker or reply.reaction}' | {message.id}")
        return self.world.reply(message=message, reply=reply)

    def _send_text_to_any_chat(self, text: str, chat_id: str, message_thread_id: str = None):
        return self.world.send_text_to_any_chat(text=text, chat_id=chat_id, message_thread_id=message_thread_id)

    def handle_message(self, message: Message):
        user_str = message.from_user.username
        chat_str = (message.chat.type or '') + (message.chat.title or '')
        self.logger.info(f"Got message from user {user_str} in chat {chat_str} | {message.id}")

        try:
            if message.filepath:
                self.handle_file(message)
            elif message.text:
                self.handle_text(message)
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
                self.world.reply(message, reply=Reply(reaction=random_reaction))

        except Exception as e:
            err_msg = '\n'.join([str(a) for a in e.args])
            self.logger.warning(err_msg)
            self._reply(message, Reply(text="Ошибка"))

    def handle_file(self, message: Message):
        self.logger.info(f"Got file {message.filepath} | {message.id}")
        if not message.filepath:
            return

        filepath = message.filepath

        if self.state == BotState.LEARN_TEXT_WAITING_TEXT:
            with open(self.file_manager(filepath), encoding="utf-8") as file:
                self.ngram_talk_module.learn_text(self.text_id, '\n'.join(file.readlines()))
                self._reply(message, reply=Reply(text=f'Текст сохранен как {self.text_id}'))
                self.state = BotState.IDLE
        elif self.state == BotState.HIDDEN_SANTA_WAITING_FILE:
            with open(self.file_manager(filepath), encoding="utf-8") as file:
                self.santa_module.initialize_from_str('\n'.join(file.readlines()))
                self._reply(message, reply=Reply(f'Прочитал! {len(self.santa_module.usernames)} юзеров и {len(self.santa_module.forbidden_pairs)} пар'))
                self.state = BotState.IDLE
        else:
            self._reply(message, reply=Reply(text="Не ожидаю файл... мне пофиг на него"))

    def handle_text(self, message: Message):
        text = message.text
        self.logger.info(f"Message text: '{text}' | {message.id}")
        # some commands are independent of current state
        if text.startswith("/send"):
            if not self.world.is_admin(message.from_user):
                self._reply(message, reply=Reply(text="У тебя нет полномочий для этого!"))
                return

            _, chat_id, message_thread_id, text = text.split(maxsplit=3)
            self._send_text_to_any_chat(chat_id=chat_id, message_thread_id=message_thread_id, text=text)
            return

        if text.startswith("/start"):
            self._reply(message, reply=Reply(text=f'Что тебе от меня надо, {message.from_user.username}'))
            self.state = BotState.IDLE
            return
        elif text.startswith("/learn_text"):
            if not self.world.is_admin(message.from_user):
                self._reply(message, reply=Reply(text="У тебя нет полномочий для этого!"))
                return
            self.state = BotState.LEARN_TEXT_WAITING_TEXT_ID
            self._reply(message, reply=Reply(text=f'Напиши название, под которым я запомню этот текст.'))
            return
        elif text.startswith("/forget_text"):
            if not self.world.is_admin(message.from_user):
                self._reply(message, reply=Reply(text="У тебя нет полномочий для этого!"))
                return
            self.state = BotState.FORGET_TEXT_WAITING_TEXT_ID
            msg = dedent(
                f"""\
                Напиши название удаляемого текста. Возможные варианты:
                {' '.join(self.ngram_talk_module.counts_per_text.keys())}
                """
            )
            self._reply(message, reply=Reply(text=msg))
            return
        elif text.startswith("/santa_init"):
            if not self.world.is_admin(message.from_user):
                self._reply(message, reply=Reply(text="У тебя нет полномочий для этого!"))
                return
            self.state = BotState.HIDDEN_SANTA_WAITING_FILE
            self._reply(message, reply=Reply(text=f'Пришли текстовый файл с юзерами и запрещенными парами.'))
            return
        elif text.startswith("/santa_start"):
            if not self.world.is_admin(message.from_user):
                self._reply(message, reply=Reply(text="У тебя нет полномочий для этого!"))
                return
            seed = text.split(maxsplit=1)[1].strip() if len(text.split()) >= 2 else None
            self.santa_module.generate_permutation(seed)
            self._reply(message, reply=Reply(text=f"Перестановка сгенерирована! Успехов! seed: '{seed}'"))
            self.state = BotState.IDLE
            return
        elif text.startswith("/santa"):
            text = self.santa_module.handle_message(message)
            self._reply(message, reply=Reply(text=text), hide_text=True)
            self.state = BotState.IDLE
            return

        if self.state == BotState.IDLE:
            text = self.ngram_talk_module.handle_message(message)
            self._reply(message, reply=Reply(text=text))
        elif self.state == BotState.LEARN_TEXT_WAITING_TEXT_ID:
            self.text_id = message.text.split("\n")[0]
            self.state = BotState.LEARN_TEXT_WAITING_TEXT
            self._reply(message, reply=Reply(text=f'Пришли текстовый файл с текстом.'))
        # elif self.state == BotState.LEARN_TEXT_WAITING_TEXT:
        #     self.ngram_talk_module.learn_text(self.text_id, message.text)
        #     self._reply(message, reply=Reply(text=f'Текст сохранен как {self.text_id}'))
        #     self.state = BotState.IDLE
        elif self.state == BotState.FORGET_TEXT_WAITING_TEXT_ID:
            text_id = message.text.split("\n")[0]
            self.ngram_talk_module.forget_text(text_id)
            self.state = BotState.IDLE
            self._reply(message, reply=Reply(text=f'Текст {text_id} удален'))
