from pymorphy3 import MorphAnalyzer
from random import random

from src.base_classes import Message
from src.modules.base import BaseModule
from .base import tokenize, detokenize, PUNKT_END_OF_SENTENCE
from .ngrams import NGramGenerator
from .swear_replacer import SwearReplacer


class TalkModule(BaseModule):
    def __init__(
            self,
            ngram_generator: NGramGenerator,
            swear_replacer: SwearReplacer,
            n_key_words: int = 5,
            n_words_in_sentence: int = 25,
            chance_new_line_after_sentence: float = 0.0,
    ):
        super().__init__()

        self.n_key_words = n_key_words
        self.chance_new_line_after_sentence = chance_new_line_after_sentence
        self.n_words_in_sentence = n_words_in_sentence

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

        key_words = [token for token in tokens if token_to_POS[token] == "NOUN"]
        if len(key_words) < self.n_key_words:
            key_words += [token for token in tokens if token_to_POS[token] == "ADJF" or token_to_POS[token] == "ADJS"]

        if len(key_words) < self.n_key_words:
            for token in tokens:
                if token_to_POS[token] not in {"NOUN", "ADJF", "ADJS"} and token.isalpha():
                    key_words.append(token)
                    if len(key_words) >= self.n_key_words:
                        break

        key_words = key_words[:self.n_key_words]
        key_words_lowered = {word.lower() for word in key_words}

        result = []
        for word in key_words:
            result.append(word.capitalize())

            n_remaining = self.n_words_in_sentence
            next_word = ""
            while n_remaining > 0 and next_word not in PUNKT_END_OF_SENTENCE:
                next_word = self.ngram_generator.generate_word(result)
                result.append(next_word)
                n_remaining -= 1

            if next_word not in PUNKT_END_OF_SENTENCE:
                result.append(".")

            if random() < self.chance_new_line_after_sentence:
                result.append("\n\n")

        result = [
            self.swear_replacer.replace_word(token) if token.lower() not in key_words_lowered else token
            for token in result
        ]

        return detokenize(result)
