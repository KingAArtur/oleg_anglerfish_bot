from abc import ABC

from src.base_classes import Message


class BaseModule(ABC):
    def __init__(self):
        pass

    def handle_message(self, message: Message) -> str:
        raise NotImplementedError
