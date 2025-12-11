import pytest

from modules import SantaModule


@pytest.fixture()
def santa_module() -> SantaModule:
    usernames = ["1", "2", "3", "4", "5", "6"]
    forbidden_pairs = [("1", "2"), ("3", "4"), ("4", "3")]

    module = SantaModule()
    module.initialize(usernames, forbidden_pairs)
    return module


def test_generate_permutation(santa_module):
    for _ in range(100):
        santa_module.generate_permutation()
        permutation = santa_module.permutation

        assert len(permutation) == len(santa_module.usernames)
        for name in santa_module.usernames:
            assert name in permutation.keys()
            assert name in permutation.values()

            assert permutation[name] != name
            assert (name, permutation[name]) not in santa_module.forbidden_pairs


@pytest.mark.parametrize("seed", ["omg", "haha", "gotcha"])
def test_generate_permutation__same_for_the_same_seed(santa_module, seed):
    santa_module.generate_permutation(seed)
    expected_permutation = santa_module.permutation

    for _ in range(5):
        santa_module.generate_permutation(seed)
        permutation = santa_module.permutation

        for name in santa_module.usernames:
            assert permutation[name] == expected_permutation[name]


def test_generate_permutation__different_for_different_seeds(santa_module):
    santa_module.generate_permutation("seed1")
    permutation_first = santa_module.permutation

    santa_module.generate_permutation("seed2")
    permutation_second = santa_module.permutation

    assert permutation_first.keys() == permutation_second.keys()
    assert permutation_first.values() != permutation_second.values()


def test_initialize_from_str(santa_module):
    s = "\n".join(
        [
            "1, 2, 3, 4, 5, 6",
            "",
            "1, 2",
            "3, 4",
            "4, 3",
        ]
    )
    santa_module_from_str = SantaModule()
    santa_module_from_str.initialize_from_str(s)

    assert santa_module_from_str.usernames == santa_module.usernames
    assert santa_module_from_str.forbidden_pairs == santa_module.forbidden_pairs


def test_only_two_logins():
    santa_module = SantaModule()
    santa_module.initialize(["1", "2"])

    santa_module.generate_permutation()
    permutation = santa_module.permutation
    assert permutation["1"] == "2"
    assert permutation["2"] == "1"

    santa_module.initialize(["1", "2"], [("1", "2")])
    with pytest.raises(StopIteration):
        santa_module.generate_permutation()
