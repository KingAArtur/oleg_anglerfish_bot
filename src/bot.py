import logging
import os
from enum import Enum
from textwrap import dedent

import telegram  # noqa https://youtrack.jetbrains.com/issue/PY-60059
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes  # noqa

from src.modules import NGramTalkModule


class BotState(Enum):
    IDLE = 1
    LEARN_TEXT_WAITING_TEXT_ID = 2
    LEARN_TEXT_WAITING_TEXT = 3
    FORGET_TEXT_WAITING_TEXT_ID = 4


class FileManager:
    def __init__(self, dir_path: str):
        if not os.path.isdir(dir_path):
            os.mkdir(path=dir_path)

        self.dir_path = dir_path

    def __call__(self, file_name: str) -> str:
        return os.path.join(self.dir_path, file_name)


class Bot:
    TMP_TEXT_FILE_NAME: str = "tmp.txt"
    NGRAM_MODULE_SAVE_FILE_NAME: str = "ngram_module_save_file.txt"

    def __init__(self):
        self.state: BotState = BotState.IDLE  # later it should be state per user or group, now its just global

        self.file_manager = FileManager(dir_path="files")

        self.ngram_talk_module: NGramTalkModule = NGramTalkModule(n=3)
        if os.path.exists(self.file_manager(self.NGRAM_MODULE_SAVE_FILE_NAME)):
            with open(self.file_manager(self.NGRAM_MODULE_SAVE_FILE_NAME), encoding="utf-8") as file:
                text = "\n".join(file.readlines())
            self.ngram_talk_module.deserialize_from_text(text)
        self.text_id: str = ""

        self.app = ApplicationBuilder().token(self.token).build()
        self.app.add_handler(MessageHandler(None, self.handle_update))

        self.logger = logging.getLogger("Bot")

    def start(self):
        self.app.run_polling()

    async def shutdown(self):
        """Saving some state before turning off"""
        self.logger.info("Shutdown!")
        if os.path.exists(self.file_manager(self.TMP_TEXT_FILE_NAME)):
            os.remove(self.file_manager(self.TMP_TEXT_FILE_NAME))

        ngram_module_serialized = self.ngram_talk_module.serialize_to_text()
        with open(self.file_manager(self.NGRAM_MODULE_SAVE_FILE_NAME), "w", encoding="utf-8") as file:
            file.write(ngram_module_serialized)

        await self.app.shutdown()

    @property
    def token(self) -> str:
        return os.getenv("BOT_TOKEN")

    def is_admin(self, user: telegram.User):
        return user.id == int(os.getenv("ADMIN_ID"))

    async def _reply(self, message: telegram.Message, text: str):
        self.logger.info(f"Sending message: {text}")
        await message.reply_text(text)

    async def handle_update(self, update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if update.message is not None:
                await self.handle_message(update.message)
            else:
                self.logger.info(f"No message in update {update.update_id}")

        except Exception as e:
            err_msg = '\n'.join(e.args)
            self.logger.warning(err_msg)
            if update.message:
                await self._reply(update.message, "Ошибка")

    async def handle_message(self, message: telegram.Message):
        if message.document:
            if self.state == BotState.LEARN_TEXT_WAITING_TEXT:
                file = await message.document.get_file()
                self.logger.info(f"Downloading the file {file.file_path}")
                with open(self.file_manager(self.TMP_TEXT_FILE_NAME), "wb") as src:
                    await file.download_to_memory(src)
                with open(self.file_manager(self.TMP_TEXT_FILE_NAME), encoding="utf-8") as src:
                    self.ngram_talk_module.learn_text(self.text_id, '\n'.join(src.readlines()))
                    await self._reply(message, f'Текст сохранен как {self.text_id}')
                    self.state = BotState.IDLE
            return

        if not message.text:
            await self._reply(f'Апчхи!')
            return

        text = message.text
        self.logger.info(f"Got message '{text}' from user {message.from_user} in chat {message.chat.type + (message.chat.title or '')}")

        # some commands are independent of current state
        if text.startswith("/start"):
            await self._reply(message, f'Старт! Твой id: {message.from_user.id}, держу в курсе!')
            self.state = BotState.IDLE
            return
        elif text.startswith("/learn_text"):
            if not self.is_admin(message.from_user):
                await self._reply(message, "У тебя нет полномочий для этого!")
                return
            self.state = BotState.LEARN_TEXT_WAITING_TEXT_ID
            await self._reply(message, f'Напиши text_id, под которым я запомню этот текст.')
            return
        elif text.startswith("/forget_text"):
            if not self.is_admin(message.from_user):
                await self._reply(message, "У тебя нет полномочий для этого!")
                return
            self.state = BotState.FORGET_TEXT_WAITING_TEXT_ID
            msg = dedent(
                f"""Напиши text_id удаляемого текста. Возможные варианты:
                {' '.join(self.ngram_talk_module.counts_per_text.keys())}
                """
            )
            await self._reply(message, msg)
            return

        if self.state == BotState.IDLE:
            text = self.ngram_talk_module.handle_message(message)
            await self._reply(message, text)
        elif self.state == BotState.LEARN_TEXT_WAITING_TEXT_ID:
            self.text_id = message.text.split("\n")[0]
            self.state = BotState.LEARN_TEXT_WAITING_TEXT
            await self._reply(message, f'Напиши сам текст или пришли его txt файлом.')
        elif self.state == BotState.LEARN_TEXT_WAITING_TEXT:
            self.ngram_talk_module.learn_text(self.text_id, message.text)
            await self._reply(message, f'Текст сохранен как {self.text_id}')
            self.state = BotState.IDLE
        elif self.state == BotState.FORGET_TEXT_WAITING_TEXT_ID:
            text_id = message.text.split("\n")[0]
            self.ngram_talk_module.forget_text(text_id)
            self.state = BotState.IDLE
            await self._reply(message, f'Текст {text_id} удален')
