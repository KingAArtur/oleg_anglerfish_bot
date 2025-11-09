from collections import defaultdict
from tqdm import tqdm
import random
import json

import nltk
from telegram import Message

from .base import BaseModule


class NGramTalkModule(BaseModule):
    def __init__(self, n: int):
        super().__init__()

        nltk.download('punkt_tab')
        self.punkt_end_of_sentence = {".", "?", "!", "..."}

        self.ngrams_to_next_word_counts: dict[tuple[str, ...], dict[str, int]] = defaultdict(dict)
        self.counts_per_text: dict[str, dict[tuple[str, ...], dict[str, int]]] = {}
        self.n = n

    def _recalculate_counts(self):
        self.ngrams_to_next_word_counts: dict[tuple[str, ...], dict[str, int]] = defaultdict(dict)

        for counts in self.counts_per_text.values():
            for ngram, next_word_counts in counts.items():
                for next_word, cnt in next_word_counts.items():
                    self.ngrams_to_next_word_counts[ngram][next_word] = (
                        self.ngrams_to_next_word_counts[ngram].get(next_word, 0) + cnt
                    )

    def learn_text(self, text_id: str, text: str):
        if text_id in self.counts_per_text:
            raise KeyError(f"Text_id {text_id} already exists")

        counts_for_this_text: dict[tuple[str, ...], dict[str, int]] = defaultdict(dict)

        tokenized_text = nltk.word_tokenize(text)
        prev_words_list = []

        for next_word in tqdm(tokenized_text, desc="Learning text..."):
            next_word = next_word.lower()

            for k in range(len(prev_words_list)):
                ngram = tuple(prev_words_list[-k - 1:])
                counts_for_this_text[ngram][next_word] = counts_for_this_text[ngram].get(next_word, 0) + 1
                self.ngrams_to_next_word_counts[ngram][next_word] = (
                    self.ngrams_to_next_word_counts[ngram].get(next_word, 0) + 1
                )

            if len(prev_words_list) < self.n:
                prev_words_list.append(next_word)
            else:
                prev_words_list = prev_words_list[1:] + [next_word]

        self.counts_per_text[text_id] = counts_for_this_text

    def forget_text(self, text_id: str):
        if text_id not in self.counts_per_text:
            raise KeyError(f"There is not text with id 'f{text_id}'")

        del self.counts_per_text[text_id]
        self._recalculate_counts()

    def _generate_sentence_from_words_list(
        self,
        words: list[str],
        n_max_words: int,
    ) -> list[str]:
        sentence_words = [word.lower() for word in words]
        for _ in range(n_max_words):
            for k in range(self.n, 0, -1):
                ngram = tuple(sentence_words[-k:])
                if ngram in self.ngrams_to_next_word_counts:
                    break
            else:
                ngram = (".",)

            if ngram not in self.ngrams_to_next_word_counts:
                break

            words = list(self.ngrams_to_next_word_counts[ngram].keys())
            counts = list(self.ngrams_to_next_word_counts[ngram].values())
            next_word = random.sample(words, counts=counts, k=1)[0]
            sentence_words.append(next_word)

            if next_word in self.punkt_end_of_sentence:
                break

        if sentence_words[-1] not in self.punkt_end_of_sentence:
            sentence_words.append(".")

        return sentence_words

    def generate_text(self, text: str, n_words_sentence_max: int = 20, n_last_words: int = 5):
        last_words = [word for word in nltk.word_tokenize(text) if word.isalpha()][-n_last_words:]

        words = []
        for word in last_words:
            sentence_words = self._generate_sentence_from_words_list([word], n_max_words=n_words_sentence_max)
            words += [sentence_words[0].capitalize()] + sentence_words[1:]

        text = " ".join(words)
        for punkt in "!?.,:)]":
            text = text.replace(" " + punkt, punkt)
        for punkt in "([":
            text = text.replace(punkt + " ", punkt)

        return text

    def handle_message(self, message: Message):
        return self.generate_text(message.text)

    def serialize_to_text(self) -> str:
        counts_per_text_with_tuples_replaced = {
            text_id: {
                NGramTalkModule.serialize_ngram(ngram): counts
                for ngram, counts in counts_for_text.items()
            }
            for text_id, counts_for_text in self.counts_per_text.items()
        }
        return json.dumps(counts_per_text_with_tuples_replaced)

    def deserialize_from_text(self, text: str):
        counts_per_text_with_tuples_replaced = json.loads(text)
        self.counts_per_text = {
            text_id: {
                NGramTalkModule.deserialize_ngram(serialized): counts
                for serialized, counts in counts_for_text.items()
            }
            for text_id, counts_for_text in counts_per_text_with_tuples_replaced.items()
        }
        self._recalculate_counts()

    @staticmethod
    def serialize_ngram(ngram: tuple[str, ...]) -> str:
        return "".join([f"{len(word)}#{word}" for word in ngram])

    @staticmethod
    def deserialize_ngram(serialized: str) -> tuple[str, ...]:
        words = []
        i = 0
        while i < len(serialized):
            length = ""
            while serialized[i] != "#":
                length += serialized[i]
                i += 1
            length = int(length)

            word = ""
            i += 1
            for _ in range(length):
                word += serialized[i]
                i += 1

            words.append(word)

        return tuple(words)
