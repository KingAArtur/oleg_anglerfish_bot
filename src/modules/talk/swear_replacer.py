from collections import defaultdict
import json

from tqdm import tqdm

from pymorphy3 import MorphAnalyzer
from pymorphy3.tagset import OpencorporaTag
from random import choice, random


class SwearReplacer:
    def __init__(
            self,
            chance_to_replace: float,
            short_swear_max_len: int = 7,
            short_swear_relative_chance: float | None = None,
    ):
        self.chance_to_replace = chance_to_replace
        self.short_swear_max_len = short_swear_max_len
        self.short_swear_relative_chance = short_swear_relative_chance

        self.tag_to_swears: dict[OpencorporaTag, list[str]] = defaultdict(list)
        self.tag_to_short_swears: dict[OpencorporaTag, list[str]] = defaultdict(list)
        self.tag_to_long_swears: dict[OpencorporaTag, list[str]] = defaultdict(list)

        self.morph = MorphAnalyzer()

    def learn_from_list(self, words: list[str], n_max: int = 10_000):
        self.tag_to_swears: dict[OpencorporaTag, list[str]] = defaultdict(list)
        self.tag_to_short_swears: dict[OpencorporaTag, list[str]] = defaultdict(list)
        self.tag_to_long_swears: dict[OpencorporaTag, list[str]] = defaultdict(list)

        for word in tqdm(words[:n_max]):
            parse = self.morph.parse(word)[0]
            tag = self.morph.parse(word)[0].tag
            self.tag_to_swears[tag].append(word)
            if len(parse.normal_form) <= self.short_swear_max_len:
                self.tag_to_short_swears[tag].append(word)
            else:
                self.tag_to_long_swears[tag].append(word)

    def replace_word(self, word: str):
        if random() > self.chance_to_replace:
            return word

        d = self.tag_to_swears
        if self.short_swear_relative_chance is not None:
            if random() < self.short_swear_relative_chance:
                d = self.tag_to_short_swears
            else:
                d = self.tag_to_long_swears

        tag = self.morph.parse(word)[0].tag
        if tag not in d:
            return word

        return choice(d[tag])

    def serialize_to_text(self) -> str:
        params = {
            "chance_to_replace": self.chance_to_replace,
            "short_swear_max_len": self.short_swear_max_len,
            "short_swear_relative_chance": self.short_swear_relative_chance,
        }
        result = json.dumps(params)

        result += "\n###\n"
        for tag, words in self.tag_to_swears.items():
            result += f"{tag}#{','.join(words)}\n"

        result += "###\n"
        for tag, words in self.tag_to_short_swears.items():
            result += f"{tag}#{','.join(words)}\n"

        result += "###\n"
        for tag, words in self.tag_to_long_swears.items():
            result += f"{tag}#{','.join(words)}\n"

        return result

    @staticmethod
    def deserialize_from_text(text: str) -> "SwearReplacer":
        params_text, words_text, short_words_text, long_words_text = text.split("###")

        params = json.loads(params_text)
        swear_replacer: SwearReplacer = SwearReplacer(
            chance_to_replace=params["chance_to_replace"],
            short_swear_relative_chance=params["short_swear_relative_chance"],
            short_swear_max_len=params["short_swear_max_len"],
        )

        for line in words_text.split("\n"):
            if line == "":
                continue
            tag_text, words_list_text = line.split("#", maxsplit=1)
            tag = OpencorporaTag(tag_text)
            for word in words_list_text.split(","):
                swear_replacer.tag_to_swears[tag].append(word)

        for line in short_words_text.split("\n"):
            if line == "":
                continue
            tag_text, words_list_text = line.split("#", maxsplit=1)
            tag = OpencorporaTag(tag_text)
            for word in words_list_text.split(","):
                swear_replacer.tag_to_short_swears[tag].append(word)

        for line in long_words_text.split("\n"):
            if line == "":
                continue
            tag_text, words_list_text = line.split("#", maxsplit=1)
            tag = OpencorporaTag(tag_text)
            for word in words_list_text.split(","):
                swear_replacer.tag_to_long_swears[tag].append(word)

        return swear_replacer
