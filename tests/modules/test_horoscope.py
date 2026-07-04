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
            "I love you!": 0.5,
            "Nobody loves you!": 0.5,
        },
        "intelligence": {
            "U r smart!": 0.5,
            "Stupid!": 0.5,
        },
        "food": {
            "You are tasty!": 0.5,
            "I would love to eat you.": 0.5,
        },
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


def test_horoscope__load_data_from_file(horoscope_module, tmp_path):
    filename = "data.json"
    with open(tmp_path / filename, "w", encoding="utf-8") as file:
        file.write(
            dedent(
                """\
                {
                    "features": {
                        "a": {
                            "aa": 0.5,
                            "aaa": 0.5
                        },
                        "b": {
                            "bb": 1.0
                        }
                    }
                }
                """
            )
        )

    horoscope_module.load_data_from_file(tmp_path / filename)

    assert horoscope_module.features == {
        "a": {
            "aa": 0.5,
            "aaa": 0.5,
        },
        "b": {
            "bb": 1.0,
        },
    }
