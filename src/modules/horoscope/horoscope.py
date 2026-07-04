import json
import random
from pathlib import Path

from src.base_classes import Message
from src.utils import today
from src.modules.base import BaseModule
from .data import DATA


class HoroscopeModule(BaseModule):
    def __init__(self, n_features: int = 6):
        super().__init__()
        self.features: dict[str, dict[str, float]] = DATA["features"]
        self.n_features = n_features

        self.dreams: dict[str, list[str]] = DATA["dreams"]

    def handle_message(self, message: Message) -> str:
        seed = f"{today()}_{message.from_user.username}"
        fixed_random = random.Random(x=seed)

        result = self.generate_text_dreams(fixed_random=fixed_random, gender=message.from_user.sex) + "\n\n"
        result += self.generate_text_features(fixed_random=fixed_random)

        if message.from_user.name:
            result = message.from_user.name + ", " + result[0].lower() + result[1:]

        return result

    def generate_text_features(self, fixed_random: random.Random) -> str:
        features = list(self.features.keys())
        fixed_random.shuffle(features)
        features = features[:self.n_features]
        result = ""

        for feature in features:
            result += fixed_random.choices(
                list(self.features[feature].keys()), weights=list(self.features[feature].values())
            )[0]
            result += "\n\n" if fixed_random.random() < 0.2 else "\n"

        return result

    def generate_text_dreams(self, fixed_random: random.Random, gender: str) -> str:
        verb_ending = "а" if gender == "w" else ''

        action_word = fixed_random.choice(self.dreams["action"]) + verb_ending
        object_word = fixed_random.choice(self.dreams["object"])
        how_word = fixed_random.choice(self.dreams["how"])

        start = fixed_random.choice(
            [
                "Мне сегодня приснилось",
                "Этой ночью мне приснилось",
                "Ночью мне приснилось",
                "Мне приснилось",
            ]
        )

        result = f"{start}, как ты {action_word} {object_word}. Выглядел{verb_ending} {how_word}!"
        return result
