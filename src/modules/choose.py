import random
from pymorphy3 import MorphAnalyzer
import re

from src.modules.base import BaseModule
from src.base_classes import Message
from src.modules.talk.base import tokenize


class ChooseModule(BaseModule):
    def __init__(self):
        super().__init__()

        self.morph = MorphAnalyzer()
        self.options_delimeter = "или"
        self.punkt_pattern = "|".join([fr"\{ch}" for ch in "!?.,:;"])

    def handle_message(self, message: Message) -> str:
        parsed_words = [self.morph.parse(word.lower())[0] for word in tokenize(message.text)]
        words_for_seed = sorted(
            [parse.normal_form for parse in parsed_words if parse.tag.POS in {"NOUN", "VERB", "ADJS", "ADJF"}]
        )
        seed = ''.join(words_for_seed)

        options = message.text.split(self.options_delimeter)
        if len(options) < 2:
            return f"Варианты-то где, емое? Раздели варианты с помощью '{self.options_delimeter}', мда."
        options[0] = re.split(pattern=self.punkt_pattern, string=options[0])[-1]
        options[-1] = re.split(pattern=self.punkt_pattern, string=options[-1])[0]
        options = sorted([option.strip() for option in options])

        fixed_random = random.Random(x=seed)
        winner = fixed_random.choice(options)

        result = f"Я утверждаю, что {winner}!\n\n"
        for option in options:
            if option == winner:
                continue
            result += f"{option.capitalize()}? {random.choice(['Фигня', 'Туфта', 'Параша', 'Дичь'])} какая-то.\n"

        return result
