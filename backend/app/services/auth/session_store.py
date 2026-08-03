from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any
from uuid import uuid4

from fastapi import Request

AUTH_SESSION_ID_KEY = "auth_session_id"
LEGACY_AUTH_PAYLOAD_KEY = "auth"


class AuthSessionStore:
    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def get(self, session_id: str | None) -> dict[str, Any] | None:
        if not session_id:
            return None
        with self._lock:
            payload = self._items.get(session_id)
            return deepcopy(payload) if payload is not None else None

    def set(self, session_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._items[session_id] = deepcopy(payload)

    def delete(self, session_id: str | None) -> None:
        if not session_id:
            return
        with self._lock:
            self._items.pop(session_id, None)

    def upsert_for_request(self, request: Request, payload: dict[str, Any]) -> str:
        session_id = request.session.get(AUTH_SESSION_ID_KEY)
        if not isinstance(session_id, str) or not session_id:
            session_id = uuid4().hex
            request.session[AUTH_SESSION_ID_KEY] = session_id
        request.session.pop(LEGACY_AUTH_PAYLOAD_KEY, None)
        self.set(session_id, payload)
        return session_id

    def get_for_request(self, request: Request) -> dict[str, Any] | None:
        session_id = request.session.get(AUTH_SESSION_ID_KEY)
        if isinstance(session_id, str) and session_id:
            payload = self.get(session_id)
            if payload is not None:
                return payload

        legacy_payload = request.session.get(LEGACY_AUTH_PAYLOAD_KEY)
        if isinstance(legacy_payload, dict):
            return deepcopy(legacy_payload)
        return None

    def clear_for_request(self, request: Request) -> None:
        session_id = request.session.get(AUTH_SESSION_ID_KEY)
        if isinstance(session_id, str) and session_id:
            self.delete(session_id)
        request.session.pop(AUTH_SESSION_ID_KEY, None)
        request.session.pop(LEGACY_AUTH_PAYLOAD_KEY, None)


_store = AuthSessionStore()


def get_auth_session_store() -> AuthSessionStore:
    return _store
