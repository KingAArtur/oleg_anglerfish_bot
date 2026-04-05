from pymorphy3 import MorphAnalyzer

from src.base_classes import Message
from src.modules.base import BaseModule
from .base import tokenize, detokenize, PUNKT_END_OF_SENTENCE
from .ngrams import NGramGenerator
from .swear_replacer import SwearReplacer


class TalkModule(BaseModule):
    N_KEY_WORDS: int = 5

    def __init__(self, ngram_generator: NGramGenerator, swear_replacer: SwearReplacer):
        super().__init__()

        self.ngram_generator = ngram_generator
        self.swear_replacer = swear_replacer

        self.morph = MorphAnalyzer()

    def handle_message(self, message: Message) -> str:
        return self.generate_text(text=message.text)

    def generate_text(self, text: str) -> str:
        tokens = tokenize(text)
        if not tokens:
            return "Апчхи!"

        token_to_POS: dict[str, str] = {token: self.morph.parse(token)[0].tag.POS for token in tokens}

        key_words: list[str] = []
        key_words += [token for token in tokens if token_to_POS[token] == "NOUN"]
        if len(key_words) < self.N_KEY_WORDS:
            key_words += [token for token in tokens if token_to_POS[token] == "ADJF" or token_to_POS[token] == "ADJS"]

        if len(key_words) < self.N_KEY_WORDS:
            for token in tokens:
                if token_to_POS[token] not in {"NOUN", "ADJF", "ADJS"}:
                    key_words.append(token)
                    if len(key_words) >= self.N_KEY_WORDS:
                        break

        result = []
        for word in key_words:
            result.append(word)

            n_remaining = 20
            next_word = ""
            while n_remaining > 0 and next_word not in PUNKT_END_OF_SENTENCE:
                next_word = self.ngram_generator.generate_word(result)
                result.append(next_word)

            if next_word not in PUNKT_END_OF_SENTENCE:
                result.append(".")

        result = [self.swear_replacer.replace_word(token) for token in result]

        return detokenize(result)
