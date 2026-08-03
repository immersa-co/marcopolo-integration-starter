from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from ..auth import UserSession


@dataclass
class ChatRun:
    chat_id: str
    message: str
    user_session: UserSession


class ChatStore:
    def __init__(self):
        self._runs: dict[str, ChatRun] = {}

    def create(self, message: str, user_session: UserSession) -> ChatRun:
        chat_run = ChatRun(chat_id=str(uuid4()), message=message, user_session=user_session)
        self._runs[chat_run.chat_id] = chat_run
        return chat_run

    def get(self, chat_id: str) -> ChatRun | None:
        return self._runs.get(chat_id)


_CHAT_STORE = ChatStore()


def get_chat_store() -> ChatStore:
    return _CHAT_STORE
