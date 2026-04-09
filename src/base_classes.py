from dataclasses import dataclass, field
from enum import Enum


class UserPrivileges(int, Enum):
    UNKNOWN = 0
    GUEST = 1
    ADMIN = 2


@dataclass
class User:
    username: str | None = None
    id: str | None = None
    name: str | None = None
    sex: str | None = None
    privileges: UserPrivileges = UserPrivileges.UNKNOWN


@dataclass
class Chat:
    type: str | None = None
    title: str | None = None
    id: str | int | None = None
    users: list[User] | None = None


@dataclass
class Message:
    text: str | None = None
    sticker: str | None = None
    filepath: str | None = None
    id: str | int | None = None
    from_user: User = field(default_factory=lambda: User())
    chat: Chat = field(default_factory=lambda: Chat())
    message_thread_id: str | None = None
