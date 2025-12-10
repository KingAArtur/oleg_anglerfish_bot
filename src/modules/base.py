from abc import ABC

from telegram import Message
from telegram.ext import ContextTypes


class BaseModule(ABC):
    def __init__(self):
        pass

    def handle_message(self, message: Message) -> str:
        raise NotImplementedError
