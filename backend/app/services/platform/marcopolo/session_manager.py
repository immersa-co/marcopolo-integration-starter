from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from ....core.config import Settings
from ....core.auth_modes import get_auth_mode_definition
from ...auth import UserSession, get_auth_session_store


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
            "developer_api_token": self._developer_api_token_session,
            "workos_connect": self._workos_connect_session,
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

    async def _developer_api_token_session(self, user_session: UserSession) -> MarcoPoloSession:
        token = self._settings.marcopolo_developer_api_token.strip()
        if not token:
            raise MarcoPoloSessionManagerError(
                "MARCOPOLO_DEVELOPER_API_TOKEN is not configured for developer_api_token mode.",
                status_code=503,
            )
        return MarcoPoloSession(access_token=token)

    async def _workos_connect_session(self, user_session: UserSession) -> MarcoPoloSession:
        if not user_session.marcopolo_provisioned:
            raise MarcoPoloSessionManagerError(
                "MarcoPolo bootstrap is required for WorkOS Standalone Connect mode.",
                status_code=401,
            )
        token = (user_session.marcopolo_access_token or "").strip()
        if not token:
            raise MarcoPoloSessionManagerError(
                "MarcoPolo authorization is required for WorkOS Standalone Connect mode. Start /api/auth/marcopolo/authorize first.",
                status_code=401,
            )
        if self._workos_connect_token_expired(user_session):
            return await self._refresh_workos_connect_session(user_session)
        return MarcoPoloSession(access_token=token)

    async def _refresh_workos_connect_session(self, user_session: UserSession) -> MarcoPoloSession:
        refresh_token = (user_session.marcopolo_refresh_token or "").strip()
        if not refresh_token:
            self._clear_workos_connect_session(user_session)
            raise MarcoPoloSessionManagerError(
                "MarcoPolo Connect session expired and cannot be refreshed. Re-establish the demo session for this user.",
                status_code=401,
            )

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self._settings.workos_connect_auth_url_effective.rstrip('/')}{self._settings.workos_connect_token_path}",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                    data={
                        "client_id": self._settings.workos_connect_client_id,
                        "client_secret": self._settings.workos_connect_client_secret,
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                )
        except httpx.HTTPError as exc:
            raise MarcoPoloSessionManagerError(
                f"WorkOS Standalone Connect token refresh failed: {_describe_exception(exc)}",
                status_code=502,
            ) from exc

        if response.status_code >= 400:
            self._clear_workos_connect_session(user_session)
            raise MarcoPoloSessionManagerError(
                "MarcoPolo Connect session expired and refresh was rejected. Re-establish the demo session for this user.",
                status_code=401,
            )

        body = response.json()
        access_token = body.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            self._clear_workos_connect_session(user_session)
            raise MarcoPoloSessionManagerError(
                "WorkOS Standalone Connect refresh response did not include a usable access token.",
                status_code=502,
            )

        refreshed_session = MarcoPoloSession(access_token=access_token.strip())
        self._persist_refreshed_workos_connect_session(
            user_session,
            access_token=refreshed_session.access_token,
            refresh_token=body.get("refresh_token"),
            id_token=body.get("id_token"),
            token_type=body.get("token_type"),
            expires_in=body.get("expires_in"),
        )
        return refreshed_session

    @staticmethod
    def _workos_connect_token_expired(user_session: UserSession) -> bool:
        expires_at = user_session.marcopolo_expires_at
        if expires_at is None:
            return False
        return expires_at <= (time.time() + 60)

    def _persist_refreshed_workos_connect_session(
        self,
        user_session: UserSession,
        *,
        access_token: str,
        refresh_token: Any,
        id_token: Any,
        token_type: Any,
        expires_in: Any,
    ) -> None:
        if not user_session.auth_session_id:
            return

        store = get_auth_session_store()
        auth_payload = store.get(user_session.auth_session_id)
        if not isinstance(auth_payload, dict):
            return

        auth_payload["marcopolo_access_token"] = access_token
        auth_payload["marcopolo_refresh_token"] = (
            refresh_token if isinstance(refresh_token, str) and refresh_token.strip() else auth_payload.get("marcopolo_refresh_token")
        )
        auth_payload["marcopolo_id_token"] = id_token if isinstance(id_token, str) and id_token.strip() else auth_payload.get("marcopolo_id_token")
        auth_payload["marcopolo_token_type"] = token_type if isinstance(token_type, str) and token_type.strip() else auth_payload.get("marcopolo_token_type")
        auth_payload["marcopolo_expires_at"] = _compute_expires_at(expires_in)
        auth_payload["marcopolo_auth_mode"] = "workos_connect"
        store.set(user_session.auth_session_id, auth_payload)

    def _clear_workos_connect_session(self, user_session: UserSession) -> None:
        if not user_session.auth_session_id:
            return

        store = get_auth_session_store()
        auth_payload = store.get(user_session.auth_session_id)
        if not isinstance(auth_payload, dict):
            return

        auth_payload["marcopolo_access_token"] = None
        auth_payload["marcopolo_refresh_token"] = None
        auth_payload["marcopolo_id_token"] = None
        auth_payload["marcopolo_token_type"] = None
        auth_payload["marcopolo_expires_at"] = None
        auth_payload["marcopolo_provisioned"] = False
        auth_payload["company"] = None
        auth_payload["namespace"] = None
        store.set(user_session.auth_session_id, auth_payload)


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
