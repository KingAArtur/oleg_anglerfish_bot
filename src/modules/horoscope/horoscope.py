import json
import random
from pathlib import Path

from src.base_classes import Message
from src.utils import today
from src.modules.base import BaseModule


class HoroscopeModule(BaseModule):
    def __init__(self, n_features: int = 6):
        super().__init__()
        self.features: dict[str, dict[str, float]] | None = None
        self.n_features = n_features

    def load_data_from_file(self, path: str | Path):
        with open(path, "r", encoding="utf-8") as file:
            content = file.read()

        data = json.loads(content)
        self.features = data["features"]

    def handle_message(self, message: Message) -> str:
        seed = f"{today()}_{message.from_user.username}"
        fixed_random = random.Random(x=seed)

        features = list(self.features.keys())
        fixed_random.shuffle(features)
        features = features[:self.n_features]
        result = ""

        for feature in features:
            result += fixed_random.choices(
                list(self.features[feature].keys()), weights=list(self.features[feature].values())
            )[0]
            result += "\n\n" if fixed_random.random() < 0.2 else "\n"

        if message.from_user.name:
            result = message.from_user.name + ", " + result[0].lower() + result[1:]

        return result
