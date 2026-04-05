import asyncio
import os
from pathlib import Path

import telegram  # noqa https://youtrack.jetbrains.com/issue/PY-60059
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes  # noqa

from src.base_classes import User, Message, Chat
from src.bot import Bot, World, Reply, BotSettings
from src.logger import DateFileLogger
from src.logger import Logger, BaseLogger


def token():
    return os.getenv("BOT_TOKEN")


class TelegramWorld(World):
    def __init__(self, bot: telegram.Bot):
        super().__init__()
        self.tg_bot: telegram.Bot = bot

    async def reply(self, message: Message, reply: Reply):
        if reply.text:
            await self.tg_bot.send_message(
                text=reply.text,
                chat_id=message.chat.id,
                message_thread_id=message.message_thread_id,
                reply_to_message_id=message.id,
            )
        elif reply.sticker:
            await self.tg_bot.send_sticker(
                chat_id=message.chat.id,
                sticker=reply.sticker,
                reply_to_message_id=message.id,
            )
        elif reply.reaction:
            await self.tg_bot.set_message_reaction(
                chat_id=message.chat.id,
                message_id=message.id,
                reaction=telegram.constants.ReactionEmoji[reply.reaction]
            )

    async def send_text_to_any_chat(self, text: str, chat_id: str, message_thread_id: str = None):
        await self.tg_bot.send_message(text=text, chat_id=chat_id, message_thread_id=message_thread_id)

    def is_admin(self, user: User) -> bool:
        return str(user.id) == os.getenv("ADMIN_ID")


class TelegramBot:
    def __init__(
        self,
        logger: Logger,
        dir_path: str | Path = Bot.DEFAULT_DIR_PATH,
        settings: BotSettings | None = None,
    ):
        self.app = ApplicationBuilder().token(token()).build()
        self.app.add_handler(MessageHandler(None, self.handle_update))

        world = TelegramWorld(bot=self.app.bot)
        self.bot = Bot(dir_path=dir_path, logger=logger, world=world, bot_settings=settings)

    def __enter__(self):
        self.app.run_polling()

    def __exit__(self, exc_type, exc_val, exc_tb):
        asyncio.run(self.app.shutdown())

    async def handle_update(self, update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
        self.bot.logger.info(f"Got update! | {update.update_id}")
        message: Message | None = None
        try:
            if update.message is not None:
                tg_message = update.message
                if (
                    tg_message.chat.type != "private"
                    and tg_message.reply_to_message is not None
                    and tg_message.reply_to_message.forum_topic_created is None
                    and tg_message.reply_to_message.from_user.id != self.app.bot.id
                ):
                    return
                user = User(username=tg_message.from_user.username, id=str(tg_message.from_user.id))
                chat = Chat(type=tg_message.chat.type, title=tg_message.chat.title, id=tg_message.chat.id)
                message = Message(
                    id=tg_message.id, from_user=user, chat=chat, message_thread_id=tg_message.message_thread_id,
                )

                if tg_message.document is not None:
                    tmp_filename = "tmp.txt"
                    file = await tg_message.document.get_file()
                    self.bot.logger.info(f"Downloading the file {file.file_path} | {tg_message.id}")
                    with self.bot.file_manager.open(tmp_filename, tmp=True, mode="wb", encoding=None) as saved:
                        await file.download_to_memory(saved)

                    message.filepath = tmp_filename
                elif tg_message.text is not None:
                    message.text = tg_message.text

                elif tg_message.sticker is not None:
                    message.sticker = tg_message.sticker.file_id

                await self.bot.handle_message(message)
            else:
                await self.bot.logger.info(f"No message in update {update.update_id}")

        except Exception as e:
            err_msg = '\n'.join(e.args)
            self.bot.logger.warning(err_msg)
            if update.message:
                await self.bot.world.reply(message=message, reply=Reply(text="Ошибка! Сори"))


def run(dir_path: str | Path = Bot.DEFAULT_DIR_PATH):
    logger = (
        DateFileLogger(name="Bot", filename="messages.log")
        if os.getenv("STAGE") == "PROD"
        else BaseLogger(name="Bot")
    )

    settings = None
    config_filepath = os.getenv("CONFIG")
    if config_filepath:
        print(f"Trying to read {config_filepath}")
        with open(config_filepath, encoding="utf-8") as file:
            content = file.read()
        settings = BotSettings.from_str(content)
        print(f"Read config succesfully!")

    tg_bot = TelegramBot(logger=logger, dir_path=dir_path, settings=settings)

    print(f"Starting...")
    with tg_bot:
        pass


if __name__ == "__main__":
    run()
