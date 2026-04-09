import pytest
from unittest.mock import patch
from random import Random

from src.modules import ChooseModule
from src.base_classes import Message


@pytest.fixture
def choose_module():
    return ChooseModule()


def test_choose_module(choose_module):
    text = "Как совунья размножается: откладывает яйца или жахается?"

    with patch.object(Random, "seed") as mock_seed:
        result = choose_module.handle_message(message=Message(text=text)).lower()

    mock_seed.assert_called_once_with("жахатьсяоткладыватьразмножатьсясовуньяяйцо")

    assert "жахается" in result.split("\n")[0]
    assert "откладывает яйца" in ''.join(result.split("\n")[1:])


def test_choose_module__consistent(choose_module):
    texts = [
        "Как совунья размножается: откладывает яйца или жахается?",
        "Совунья как размножается: откладывает яйца или жахается?",
        "Как совунья размножается: жахается или откладывает яйца?",
        "Совунья как размножается: жахается или откладывает яйца?",
        "Ну и как совунья размножается: откладывает яйца или жахается?",
        "Ну и как же совунья размножается: откладывает яйца или жахается?",
        "Как же совунья размножается: откладывает яйца или жахается?",
    ]

    results = set()

    for text in texts:
        for _ in range(10):
            result = choose_module.handle_message(message=Message(text=text)).split("\n")[0].lower()
            results.add(result)

    assert len(results) == 1
    result = results.pop()

    assert "жахается" in result
    assert "откладывает яйца" not in result


def test_choose_module__no_options(choose_module):
    text = "Как совунья размножается: откладывает яйца?"

    result = choose_module.handle_message(message=Message(text=text))

    assert result == "Варианты-то где, емое? Раздели варианты с помощью 'или', мда."
