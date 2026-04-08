from dataclasses import dataclass, field


@dataclass
class User:
    username: str | None = None
    id: str | None = None


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
