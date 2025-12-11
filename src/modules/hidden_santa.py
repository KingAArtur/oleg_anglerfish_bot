import random

from telegram import Message

from .base import BaseModule


N_MAX_ATTEMPTS = 100


def generate_permutation(
    names: list[str],
    forbidden_pairs: list[tuple[str, str]] | None = None,
    seed: str | None = None
) -> dict[str, str]:
    random.seed(seed)

    if forbidden_pairs is None:
        forbidden_pairs = []

    for _ in range(N_MAX_ATTEMPTS):
        receivers = names[:]
        random.shuffle(receivers)

        permutation = dict()
        for sender, receiver in zip(names, receivers):
            if sender == receiver or (sender, receiver) in forbidden_pairs:
                break
            permutation[sender] = receiver

        if len(permutation) != len(names):
            continue

        return permutation
    else:
        raise StopIteration(f"Max {N_MAX_ATTEMPTS} attempts reached, couldn't generate permutation")


class SantaModule(BaseModule):
    def __init__(self):
        super().__init__()
        self.usernames: list[str] | None = None
        self.forbidden_pairs: list[tuple[str, str]] | None = None
        self.permutation: dict[str, str] | None = None

    def initialize(self, usernames: list[str], forbidden_pairs: list[tuple[str, str]] | None = None):
        self.usernames = usernames
        self.forbidden_pairs = forbidden_pairs if forbidden_pairs is not None else []
        self.permutation = None

    def initialize_from_str(self, s: str):
        """
        login1,login2,login3,login4
        login1,login2
        login2,login1
        """
        s = [t for t in s.replace(' ', '').split("\n") if len(t) > 0]
        usernames = s[0].split(",")

        forbidden_pairs = []
        if len(s) > 1:
            for pair_str in s[1:]:
                pair = pair_str.split(",")
                if len(pair) != 2:
                    raise KeyError(f"{pair_str} contains {len(pair)} logins, should be 2")
                forbidden_pairs.append((pair[0], pair[1]))

        self.initialize(usernames, forbidden_pairs)

    def generate_permutation(self, seed: str | None = None):
        if self.usernames is None:
            raise ValueError("Usernames list is not initialized")

        self.permutation = generate_permutation(self.usernames, self.forbidden_pairs, seed)

    def handle_message(self, message: Message) -> str:
        if self.permutation is None:
            return "Santa is not initialized yet! Generate permutation pls"

        username = message.from_user.username
        if username not in self.permutation:
            return f"Your username {username} is not in permutation! Sorry about that ^^"

        return f"Ты, {username}, даришь подарок @{self.permutation[username]}! Такие дела."
