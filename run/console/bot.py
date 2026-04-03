from base_classes import User, Message, Chat
from src.bot import Bot, World, Reply
from src.logger import FileLogger
import asyncio


class ConsoleWorld(World):
    async def reply(self, message: Message, reply: Reply):
        content = reply.text or reply.sticker or reply.reaction

        print(content)

    def is_admin(self, user: User) -> bool:
        return True


def run(bot: Bot):
    user = User(username="local_user")
    chat = Chat(type="local", title="Local_chat", id="")

    with bot:
        while True:
            try:
                text = input().strip()
                if text.startswith("/file "):
                    text = text[len("/file "):]
                    message = Message(filepath=text)
                else:
                    message = Message(text=text)

                message.from_user = user
                message.chat = chat
                asyncio.run(bot.handle_message(message))
            except KeyboardInterrupt:
                break


if __name__ == "__main__":
    bot = Bot(logger=FileLogger(name="Bot", filename="local.log"), world=ConsoleWorld())
    run(bot)
