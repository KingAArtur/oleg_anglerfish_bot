import pytest
from collections import defaultdict

from src.modules.talk import SwearReplacer


WORDS = ["птица", "упала", "в", "комнату"]
N = 1000


@pytest.fixture
def swear_replacer():
    swears = [
        "курица",
        "проститутка",
        "уплыла",
        "всплакнула",
        "фабрику",
        "квартиру",
    ]

    replacer = SwearReplacer(chance_to_replace=1.0, short_swear_max_len=7, short_swear_relative_chance=1.0)
    replacer.learn_from_list(swears)
    return replacer


def test_learn_from_list(swear_replacer):
    first_tag = swear_replacer.morph.parse("птица")[0].tag
    second_tag = swear_replacer.morph.parse("упала")[0].tag
    third_tag = swear_replacer.morph.parse("комнату")[0].tag

    assert swear_replacer.tag_to_swears == {
        first_tag: ["курица", "проститутка"],
        second_tag: ["уплыла", "всплакнула"],
        third_tag: ["фабрику", "квартиру"],
    }
    assert swear_replacer.tag_to_short_swears == {
        first_tag: ["курица"],
        second_tag: ["уплыла"],
        third_tag: ["фабрику"],
    }
    assert swear_replacer.tag_to_long_swears == {
        first_tag: ["проститутка"],
        second_tag: ["всплакнула"],
        third_tag: ["квартиру"],
    }


def test_replacer_basic__0_0(swear_replacer):
    swear_replacer.chance_to_replace = 0.0

    for _ in range(N):
        result = [swear_replacer.replace_word(word) for word in WORDS]
        assert result == WORDS


def test_replacer_basic__0_5(swear_replacer):
    swear_replacer.chance_to_replace = 0.5
    swear_replacer.short_swear_relative_chance = None

    results = defaultdict(int)
    for _ in range(N):
        result = swear_replacer.replace_word("птица")
        results[result] += 1

    assert results["птица"] + results["курица"] + results["проститутка"] == N
    assert abs(results["птица"] / N - 0.5) < 0.1
    assert abs(results["курица"] / N - 0.25) < 0.05
    assert abs(results["проститутка"] / N - 0.25) < 0.05


def test_replacer_basic__1_0(swear_replacer):
    swear_replacer.chance_to_replace = 1.0
    swear_replacer.short_swear_relative_chance = None

    results = defaultdict(int)
    for _ in range(N):
        result = swear_replacer.replace_word("птица")
        results[result] += 1

    assert results["птица"] + results["курица"] + results["проститутка"] == N
    assert results["птица"] == 0
    assert abs(results["курица"] / N - 0.5) < 0.1
    assert abs(results["проститутка"] / N - 0.5) < 0.1


def test_replacer_only_shorts(swear_replacer):
    swear_replacer.chance_to_replace = 1.0
    swear_replacer.short_swear_relative_chance = 1.0

    for _ in range(N):
        result = [swear_replacer.replace_word(word) for word in WORDS]
        assert result == ["курица", "уплыла", "в", "фабрику"]


def test_replacer_only_longs(swear_replacer):
    swear_replacer.chance_to_replace = 1.0
    swear_replacer.short_swear_relative_chance = 0.0

    for _ in range(N):
        result = [swear_replacer.replace_word(word) for word in WORDS]
        assert result == ["проститутка", "всплакнула", "в", "квартиру"]


def test_replacer_serialize(swear_replacer):
    serialized_str = swear_replacer.serialize_to_text()
    new_replacer = SwearReplacer.deserialize_from_text(serialized_str)

    assert new_replacer.chance_to_replace == swear_replacer.chance_to_replace
    assert new_replacer.short_swear_relative_chance == swear_replacer.short_swear_relative_chance
    assert new_replacer.short_swear_max_len == swear_replacer.short_swear_max_len

    assert new_replacer.tag_to_swears == swear_replacer.tag_to_swears
    assert new_replacer.tag_to_short_swears == swear_replacer.tag_to_short_swears
    assert new_replacer.tag_to_long_swears == swear_replacer.tag_to_long_swears


def test_empty_replacer():
    swear_replacer = SwearReplacer(chance_to_replace=1.0)
    word = "птица"
    result = swear_replacer.replace_word(word)
    assert result == word
