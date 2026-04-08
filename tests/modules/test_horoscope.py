import pytest
from freezegun import freeze_time

from src.base_classes import Message, User
from src.modules import HoroscopeModule


@pytest.fixture
def horoscope_module() -> HoroscopeModule:
    return HoroscopeModule()


def test_horoscope__same_answers(horoscope_module):
    msg = Message(from_user=User(username="first"))
    results = set()

    with freeze_time("2026-04-10"):
        for _ in range(10):
            results.add(horoscope_module.handle_message(msg))

    assert len(results) == 1


def test_horoscope__different_answers_for_different_users(horoscope_module):
    n = 10
    results = set()

    with freeze_time("2026-04-10"):
        for i in range(n):
            msg = Message(from_user=User(username=f"{i}"))

            results.add(horoscope_module.handle_message(msg))

    assert len(results) == n


def test_horoscope__different_results_for_different_days(horoscope_module):
    n = 9
    results = set()

    for i in range(n):
        with freeze_time(f"2026-04-0{i + 1}"):
            msg = Message(from_user=User(username=f"first"))

            results.add(horoscope_module.handle_message(msg))

    assert len(results) == n
