from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from ....core.config import Settings
from ....core.auth_modes import get_auth_mode_definition
from ...auth import UserSession, get_auth_session_store
from ...auth.namespace_tokens import (
    NamespaceTokenError,
    issue_namespace_user_token,
)


class MarcoPoloSessionManagerError(RuntimeError):
    def __init__(self, detail: str, status_code: int = 502):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass
class MarcoPoloSession:
    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = None
    expires_at: float | None = None


class MarcoPoloSessionManager:
    """Resolve and refresh the MarcoPolo auth session for the current user."""

    def __init__(self, settings: Settings):
        self._settings = settings

    async def resolve_session(self, user_session: UserSession) -> MarcoPoloSession:
        if user_session.user is None:
            raise MarcoPoloSessionManagerError("User session is not authenticated.", status_code=401)

        auth_mode = user_session.marcopolo_auth_mode or self._settings.marcopolo_auth_mode_effective
        mode_definition = get_auth_mode_definition(auth_mode)
        if mode_definition is None:
            raise MarcoPoloSessionManagerError(
                f"Unsupported MarcoPolo auth mode: {auth_mode}",
                status_code=503,
            )

        session_factory = {
            "namespace_key": self._namespace_key_session,
            "developer_api_token": self._developer_api_token_session,
        }.get(auth_mode)

        if session_factory is None:
            raise MarcoPoloSessionManagerError(
                f"MarcoPolo auth mode {auth_mode} is not wired into the service layer.",
                status_code=503,
            )

        if not mode_definition.implemented:
            raise MarcoPoloSessionManagerError(
                f"MarcoPolo auth mode {auth_mode} is documented but not implemented in the demo yet.",
                status_code=503,
            )

        return await session_factory(user_session)

    async def _namespace_key_session(self, user_session: UserSession) -> MarcoPoloSession:
        token = (user_session.marcopolo_access_token or "").strip()
        expires_at = user_session.marcopolo_expires_at
        # Namespace user tokens live 300 seconds; re-exchange the namespace key
        # rather than refreshing, keeping a 60-second safety margin.
        if token and expires_at and expires_at > (time.time() + 60):
            return MarcoPoloSession(access_token=token, expires_at=expires_at)

        email = user_session.user.email if user_session.user else None
        try:
            issued = await issue_namespace_user_token(self._settings, email or "")
        except NamespaceTokenError as exc:
            raise MarcoPoloSessionManagerError(exc.detail, status_code=exc.status_code) from exc

        self._persist_namespace_key_session(user_session, issued)
        return MarcoPoloSession(
            access_token=issued.access_token,
            expires_at=issued.expires_at,
        )

    def _persist_namespace_key_session(self, user_session: UserSession, issued) -> None:
        if not user_session.auth_session_id:
            return

        store = get_auth_session_store()
        auth_payload = store.get(user_session.auth_session_id)
        if not isinstance(auth_payload, dict):
            return

        auth_payload["marcopolo_access_token"] = issued.access_token
        auth_payload["marcopolo_refresh_token"] = None
        auth_payload["marcopolo_token_type"] = "Bearer"
        auth_payload["marcopolo_expires_at"] = issued.expires_at
        auth_payload["marcopolo_auth_mode"] = "namespace_key"
        auth_payload["marcopolo_provisioned"] = True
        auth_payload["company"] = issued.company
        auth_payload["namespace"] = issued.namespace
        store.set(user_session.auth_session_id, auth_payload)

    async def _developer_api_token_session(self, user_session: UserSession) -> MarcoPoloSession:
        token = self._settings.marcopolo_developer_api_token.strip()
        if not token:
            raise MarcoPoloSessionManagerError(
                "MARCOPOLO_DEVELOPER_API_TOKEN is not configured for developer_api_token mode.",
                status_code=503,
            )
        return MarcoPoloSession(access_token=token)


def _describe_exception(exc: BaseException) -> str:
    if isinstance(exc, BaseExceptionGroup):
        parts = [_describe_exception(item) for item in exc.exceptions]
        parts = [part for part in parts if part]
        if parts:
            return " | ".join(parts)
    if isinstance(exc, httpx.HTTPStatusError):
        return _describe_http_status_error(exc)
    detail = str(exc).strip()
    return detail or exc.__class__.__name__


def _describe_http_status_error(exc: httpx.HTTPStatusError) -> str:
    response = exc.response
    detail = response.reason_phrase or ""
    request_url = str(response.request.url) if response.request else ""
    if request_url:
        return f"HTTP {response.status_code} {detail} for url '{request_url}'".strip()
    return f"HTTP {response.status_code} {detail}".strip()


def _compute_expires_at(expires_in: Any) -> float | None:
    if isinstance(expires_in, (int, float)):
        ttl = float(expires_in)
    elif isinstance(expires_in, str):
        try:
            ttl = float(expires_in)
        except ValueError:
            return None
    else:
        return None

    if ttl <= 0:
        return None
    return time.time() + ttl
