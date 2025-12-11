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


def test_equal_distribution():
    usernames = ["1", "2", "3", "4", "5", "6"]
    santa_module = SantaModule()
    santa_module.initialize(usernames)

    counts = {
        name: {name: 0 for name in usernames}
        for name in usernames
    }

    N_ATTEMPTS = 1000
    MIN_PROPORTION_COEF = 0.7
    for _ in range(N_ATTEMPTS):
        santa_module.generate_permutation()
        for sender, receiver in santa_module.permutation.items():
            counts[sender][receiver] += 1

    for sender in usernames:
        assert sum(counts[sender].values()) == N_ATTEMPTS
        for receiver in usernames:
            if receiver == sender:
                continue
            assert counts[sender][receiver] >= MIN_PROPORTION_COEF * (N_ATTEMPTS / (len(usernames) - 1))


def test_equal_distribution__forbidden_pairs(santa_module):
    usernames = santa_module.usernames

    counts = {
        name: {name: 0 for name in usernames}
        for name in usernames
    }
    # distribution is not equal because of forbidden pairs, but I am lazy to calculate
    expected_proportions = {
        "1": {
            "1": 0.0,
            "2": 0.0,
            "3": 0.25,
            "4": 0.25,
            "5": 0.25,
            "6": 0.25,
        },
        "2": {
            "1": 0.0,
            "2": 0.2,
            "3": 0.2,
            "4": 0.2,
            "5": 0.2,
            "6": 0.2,
        },
        "3": {
            "1": 0.25,
            "2": 0.25,
            "3": 0.0,
            "4": 0.0,
            "5": 0.25,
            "6": 0.25,
        },
        "4": {
            "1": 0.25,
            "2": 0.25,
            "3": 0.0,
            "4": 0.0,
            "5": 0.25,
            "6": 0.25,
        },
        "5": {
            "1": 0.2,
            "2": 0.2,
            "3": 0.2,
            "4": 0.2,
            "5": 0.0,
            "6": 0.2,
        },
        "6": {
            "1": 0.2,
            "2": 0.2,
            "3": 0.2,
            "4": 0.2,
            "5": 0.2,
            "6": 0.0,
        },
    }

    N_ATTEMPTS = 1000
    MIN_PROPORTION_COEF = 0.7
    for _ in range(N_ATTEMPTS):
        santa_module.generate_permutation()
        for sender, receiver in santa_module.permutation.items():
            counts[sender][receiver] += 1

    for sender in usernames:
        assert sum(counts[sender].values()) == N_ATTEMPTS
        for receiver in usernames:
            if receiver == sender or (sender, receiver) in santa_module.forbidden_pairs:
                continue
            assert counts[sender][receiver] >= MIN_PROPORTION_COEF * expected_proportions[sender][receiver] * N_ATTEMPTS
