from __future__ import annotations

from dataclasses import dataclass
import re
import time
from typing import Any
from urllib.parse import urlencode, urljoin
from uuid import uuid4

import httpx
from fastapi import Request
from fastapi.responses import RedirectResponse

from ...core.config import Settings
from ...core.auth_modes import get_auth_mode_definition
from ...models.api import UserProfile
from .namespace_tokens import NamespaceTokenError, issue_namespace_user_token
from .session_store import get_auth_session_store

_MARCOPOLO_AUTH_MODE_SESSION_KEY = "marcopolo_auth_mode"
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class UserSession:
    authenticated: bool
    user: UserProfile | None
    auth_session_id: str | None = None
    id_token: str | None = None
    access_token: str | None = None
    provider: str | None = None
    marcopolo_auth_mode: str | None = None
    marcopolo_provisioned: bool = False
    marcopolo_access_token: str | None = None
    marcopolo_refresh_token: str | None = None
    marcopolo_id_token: str | None = None
    marcopolo_token_type: str | None = None
    marcopolo_expires_at: float | None = None
    company: str | None = None
    namespace: str | None = None


def user_session_from_auth_payload(
    auth_payload: dict[str, Any] | None,
    *,
    auth_session_id: str | None = None,
) -> UserSession:
    if not auth_payload:
        return UserSession(authenticated=False, user=None)

    return UserSession(
        authenticated=True,
        user=UserProfile.model_validate(auth_payload["user"]),
        auth_session_id=auth_session_id,
        id_token=auth_payload.get("id_token"),
        access_token=auth_payload.get("access_token"),
        provider=auth_payload.get("provider"),
        marcopolo_auth_mode=auth_payload.get("marcopolo_auth_mode"),
        marcopolo_provisioned=bool(auth_payload.get("marcopolo_provisioned")),
        marcopolo_access_token=auth_payload.get("marcopolo_access_token"),
        marcopolo_refresh_token=auth_payload.get("marcopolo_refresh_token"),
        marcopolo_id_token=auth_payload.get("marcopolo_id_token"),
        marcopolo_token_type=auth_payload.get("marcopolo_token_type"),
        marcopolo_expires_at=_coerce_float(auth_payload.get("marcopolo_expires_at")),
        company=auth_payload.get("company"),
        namespace=auth_payload.get("namespace"),
    )


class AuthPlatformError(RuntimeError):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def validate_marcopolo_email_identity(user: UserProfile | None) -> str:
    email = (user.email or "").strip() if user else ""
    if not email:
        raise AuthPlatformError(
            "The signed-in identity provider did not return an email address required for MarcoPolo authorization.",
            status_code=400,
        )

    return email


class AuthPlatformService:
    def __init__(self, settings: Settings):
        self._settings = settings

    @property
    def auth_required(self) -> bool:
        return self._settings.auth_required

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.session_secret.strip())

    def selected_marcopolo_auth_mode(self, request: Request) -> str:
        selected = request.session.get(_MARCOPOLO_AUTH_MODE_SESSION_KEY)
        if isinstance(selected, str) and get_auth_mode_definition(selected):
            return selected
        return self._settings.marcopolo_auth_mode_effective

    def set_selected_marcopolo_auth_mode(self, request: Request, mode: str) -> str:
        definition = get_auth_mode_definition(mode)
        if definition is None:
            raise AuthPlatformError(f"Unknown MarcoPolo auth mode: {mode}", status_code=404)
        if not definition.implemented:
            raise AuthPlatformError(
                f"MarcoPolo auth mode {mode} is documented but not implemented in the demo yet.",
                status_code=400,
            )

        request.session[_MARCOPOLO_AUTH_MODE_SESSION_KEY] = mode
        auth_payload = get_auth_session_store().get_for_request(request)
        if isinstance(auth_payload, dict) and "user" in auth_payload:
            get_auth_session_store().upsert_for_request(
                request,
                _normalized_auth_payload_for_mode(auth_payload, mode),
            )
        return mode

    def create_demo_session(self, request: Request, email: str) -> UserSession:
        normalized_email = email.strip().lower()
        if not _EMAIL_PATTERN.match(normalized_email):
            raise AuthPlatformError("Enter a valid demo user email address.", status_code=422)

        selected_mode = self.selected_marcopolo_auth_mode(request)
        user = UserProfile(
            provider="demo_session",
            provider_subject=normalized_email,
            subject=f"demo_session:{normalized_email}",
            email=normalized_email,
            name=normalized_email,
            issuer="marcopolo-integration-starter",
            email_verified=True,
        )
        auth_payload = {
            "provider": "demo_session",
            "user": user.model_dump(mode="json"),
            "issuer": user.issuer,
            "marcopolo_auth_mode": selected_mode,
            "marcopolo_provisioned": False,
        }
        get_auth_session_store().upsert_for_request(
            request,
            _normalized_auth_payload_for_mode(auth_payload, selected_mode),
        )
        return user_session_from_auth_payload(get_auth_session_store().get_for_request(request))

    async def authorize_marcopolo_connect(
        self,
        request: Request,
        user_session: UserSession,
        *,
        return_to: str | None = None,
    ) -> RedirectResponse:
        if not user_session.authenticated or user_session.user is None:
            raise AuthPlatformError("Sign in is required before authorizing MarcoPolo.", status_code=401)
        selected_mode = user_session.marcopolo_auth_mode or self._settings.marcopolo_auth_mode_effective
        if selected_mode == "namespace_key":
            return await self._authorize_namespace_key(request, user_session, return_to=return_to)
        raise AuthPlatformError(
            f"MarcoPolo auth mode '{selected_mode}' does not use redirect authorization.",
            status_code=409,
        )

    async def _authorize_namespace_key(
        self,
        request: Request,
        user_session: UserSession,
        *,
        return_to: str | None,
    ) -> RedirectResponse:
        try:
            issued = await issue_namespace_user_token(
                self._settings, user_session.user.email or ""
            )
        except NamespaceTokenError as exc:
            raise AuthPlatformError(exc.detail, status_code=exc.status_code) from exc

        auth_payload = get_auth_session_store().get_for_request(request)
        if not isinstance(auth_payload, dict) or "user" not in auth_payload:
            raise AuthPlatformError(
                "The Integration Demo session is missing.", status_code=401
            )
        auth_payload["marcopolo_access_token"] = issued.access_token
        auth_payload["marcopolo_refresh_token"] = None
        auth_payload["marcopolo_token_type"] = "Bearer"
        auth_payload["marcopolo_expires_at"] = issued.expires_at
        auth_payload["marcopolo_auth_mode"] = "namespace_key"
        auth_payload["marcopolo_provisioned"] = True
        auth_payload["company"] = issued.company
        auth_payload["namespace"] = issued.namespace
        get_auth_session_store().upsert_for_request(request, auth_payload)

        return RedirectResponse(
            url=return_to or self._default_return_url(with_auth_success=True),
            status_code=302,
        )

    def clear_session(self, request: Request) -> None:
        selected_mode = self.selected_marcopolo_auth_mode(request)
        get_auth_session_store().clear_for_request(request)
        request.session.clear()
        request.session[_MARCOPOLO_AUTH_MODE_SESSION_KEY] = selected_mode

    def _default_return_url(self, *, with_auth_success: bool) -> str:
        target = self._settings.auth_default_return_url or self._settings.frontend_base_url
        if not with_auth_success:
            return target
        separator = "&" if "?" in target else "?"
        return f"{target}{separator}{urlencode({'auth': 'success'})}"



def _normalized_auth_payload_for_mode(auth_payload: dict[str, Any], mode: str) -> dict[str, Any]:
    normalized = dict(auth_payload)
    normalized["marcopolo_auth_mode"] = mode
    _clear_marcopolo_auth_state(normalized)
    return normalized


def _clear_marcopolo_auth_state(auth_payload: dict[str, Any]) -> None:
    auth_payload["marcopolo_access_token"] = None
    auth_payload["marcopolo_refresh_token"] = None
    auth_payload["marcopolo_id_token"] = None
    auth_payload["marcopolo_token_type"] = None
    auth_payload["marcopolo_expires_at"] = None
    auth_payload["marcopolo_provisioned"] = False
    auth_payload["company"] = None
    auth_payload["namespace"] = None





def _coerce_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None
