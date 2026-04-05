import json
import random
from collections import defaultdict

from tqdm import tqdm


class NGramGenerator:
    def __init__(self, n: int):
        super().__init__()

        self.ngrams_to_next_word_counts: dict[tuple[str, ...], dict[str, float]] = defaultdict(dict)
        self.counts_per_text: dict[str, dict[tuple[str, ...], dict[str, float]]] = {}
        self.n = n

    def recalculate_counts(self):
        self.ngrams_to_next_word_counts: dict[tuple[str, ...], dict[str, float]] = defaultdict(dict)

        for counts in self.counts_per_text.values():
            for ngram, next_word_counts in counts.items():
                for next_word, cnt in next_word_counts.items():
                    self.ngrams_to_next_word_counts[ngram][next_word] = (
                        self.ngrams_to_next_word_counts[ngram].get(next_word, 0) + cnt
                    )

    def learn_text(self, text_id: str, text: list[str]):
        if text_id in self.counts_per_text:
            raise KeyError(f"Text_id {text_id} already exists")

        counts_for_this_text: dict[tuple[str, ...], dict[str, int]] = defaultdict(dict)

        prev_words_list = []

        for next_word in tqdm(text, desc="Learning text..."):
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
        self.recalculate_counts()

    def generate_word(self, words: list[str]) -> str:
        words_lowered = [word.lower() for word in words]
        for k in range(self.n, 0, -1):
            ngram = tuple(words_lowered[-k:])
            if ngram in self.ngrams_to_next_word_counts:
                break
        else:
            return "?"

        counts = self.ngrams_to_next_word_counts[ngram]
        variants, weights = list(counts.keys()), list(counts.values())
        return random.choices(population=variants, weights=weights, k=1)[0]

    def serialize_to_text(self) -> str:
        counts_per_text_with_tuples_replaced = {
            text_id: {
                NGramGenerator.serialize_ngram(ngram): counts
                for ngram, counts in counts_for_text.items()
            }
            for text_id, counts_for_text in self.counts_per_text.items()
        }
        return f"{self.n}\n" + json.dumps(counts_per_text_with_tuples_replaced)

    @staticmethod
    def deserialize_from_text(text: str) -> "NGramGenerator":
        text_n, text_rest = text.split('\n', maxsplit=1)

        n = int(text_n)
        ngram_generator = NGramGenerator(n=n)

        counts_per_text_with_tuples_replaced = json.loads(text_rest)
        ngram_generator.counts_per_text = {
            text_id: {
                NGramGenerator.deserialize_ngram(serialized): counts
                for serialized, counts in counts_for_text.items()
            }
            for text_id, counts_for_text in counts_per_text_with_tuples_replaced.items()
        }
        ngram_generator.recalculate_counts()

        return ngram_generator

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
