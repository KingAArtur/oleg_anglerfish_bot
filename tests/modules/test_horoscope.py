import random

import pytest
from freezegun import freeze_time
from textwrap import dedent

from src.base_classes import Message, User
from src.modules import HoroscopeModule


@pytest.fixture
def horoscope_module() -> HoroscopeModule:
    horoscope_module = HoroscopeModule(n_features=1)
    horoscope_module.features = {
        "love": {
            "Люблю!": 0.5,
            "Не люблю!": 0.5,
        },
        "intelligence": {
            "Умница!": 0.5,
            "Тупица": 0.5,
        },
        "food": {
            "Вкуснятина!": 0.5,
            "Аппетитно!": 0.5,
        },
    }
    horoscope_module.dreams = {
        "action": ["отжарил"],
        "object": ["курицу"],
        "how": ["аппетитно"],
    }
    return horoscope_module


@pytest.fixture
def users() -> list[User]:
    return [User(username=f"{i}") for i in range(3)]


def test_horoscope__same_answers(horoscope_module, users):
    with freeze_time("2026-04-10"):
        for user in users:
            results = set()
            msg = Message(from_user=user)
            for _ in range(100):
                results.add(horoscope_module.handle_message(msg))

            assert len(results) == 1


def test_horoscope__different_answers_for_different_users(horoscope_module, users):
    assert len(users) > 1

    results = set()
    with freeze_time("2026-04-10"):
        for user in users:
            msg = Message(from_user=user)
            results.add(horoscope_module.handle_message(msg))

    assert len(results) == len(users)


def test_horoscope__different_results_for_different_days(horoscope_module, users):
    n = 7
    results = set()

    for i in range(n):
        with freeze_time(f"2026-04-0{i + 1}"):
            msg = Message(from_user=users[0])
            results.add(horoscope_module.handle_message(msg))

    assert len(results) == n


def test_horoscope__generate_text_dreams(horoscope_module):
    fixed_random = random.Random(x=42)
    result = horoscope_module.generate_text_dreams(fixed_random=fixed_random, gender="m")
    assert result == "Этой ночью мне приснилось, как ты отжарил курицу. Выглядел аппетитно!"

    fixed_random = random.Random(x=42)
    result = horoscope_module.generate_text_dreams(fixed_random=fixed_random, gender="w")
    assert result == "Этой ночью мне приснилось, как ты отжарила курицу. Выглядела аппетитно!"
