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
from .session_store import get_auth_session_store

_WORKOS_CONNECT_RETURN_TO_SESSION_KEY = "workos_connect_return_to"
_WORKOS_CONNECT_STATE_SESSION_KEY = "workos_connect_state"
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


@dataclass(frozen=True)
class MarcoPoloBootstrap:
    redirect_url: str
    company: str
    namespace: str


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
        if selected_mode != "workos_connect":
            raise AuthPlatformError("MarcoPolo auth mode is not set to workos_connect.", status_code=409)
        if not self._settings.workos_connect_configured:
            raise AuthPlatformError("WorkOS Standalone Connect is not configured for this environment.", status_code=503)
        validate_marcopolo_email_identity(user_session.user)

        state = uuid4().hex
        request.session[_WORKOS_CONNECT_STATE_SESSION_KEY] = state
        request.session[_WORKOS_CONNECT_RETURN_TO_SESSION_KEY] = (
            return_to or self._default_return_url(with_auth_success=True)
        )
        return RedirectResponse(url=self._build_workos_connect_authorize_url(state), status_code=302)

    async def handle_workos_connect_login(
        self,
        request: Request,
        user_session: UserSession,
        *,
        external_auth_id: str | None,
    ) -> RedirectResponse:
        if not external_auth_id:
            raise AuthPlatformError("AuthKit did not provide external_auth_id.", status_code=400)

        if not user_session.authenticated or user_session.user is None:
            raise AuthPlatformError(
                "Create a demo app session before continuing WorkOS Standalone Connect authorization.",
                status_code=401,
            )

        if not self._settings.workos_connect_configured:
            raise AuthPlatformError("WorkOS Standalone Connect is not configured for this environment.", status_code=503)
        validate_marcopolo_email_identity(user_session.user)

        user = user_session.user
        first_name, last_name = _split_name(user.name)
        external_user_id = f"uid_{(user.email or '').strip().lower()}"
        payload: dict[str, Any] = {
            "external_auth_id": external_auth_id,
            "user": {
                "id": external_user_id,
                "email": user.email,
                "name": user.name,
            },
        }
        if first_name:
            payload["user"]["first_name"] = first_name
        if last_name:
            payload["user"]["last_name"] = last_name

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self._workos_connect_complete_url(),
                headers={
                    "Authorization": f"Bearer {self._settings.workos_api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
            )

        if response.status_code >= 400:
            raise AuthPlatformError(
                f"WorkOS Standalone Connect completion failed with {response.status_code}: {response.text}",
                status_code=502,
            )

        body = response.json()
        redirect_uri = body.get("redirect_uri")
        if not isinstance(redirect_uri, str) or not redirect_uri:
            raise AuthPlatformError("WorkOS Standalone Connect completion did not return redirect_uri.", status_code=502)

        return RedirectResponse(url=redirect_uri, status_code=302)

    async def complete_workos_connect(self, request: Request) -> RedirectResponse:
        if not self._settings.workos_connect_configured:
            raise AuthPlatformError("WorkOS Standalone Connect is not configured for this environment.", status_code=503)

        error = request.query_params.get("error")
        if error:
            description = request.query_params.get("error_description") or error
            raise AuthPlatformError(f"WorkOS Standalone Connect authorization failed: {description}", status_code=400)

        returned_state = request.query_params.get("state")
        expected_state = request.session.pop(_WORKOS_CONNECT_STATE_SESSION_KEY, None)
        if not expected_state or returned_state != expected_state:
            raise AuthPlatformError("WorkOS Standalone Connect state validation failed.", status_code=400)

        code = request.query_params.get("code")
        if not code:
            raise AuthPlatformError("WorkOS Standalone Connect callback did not include an authorization code.", status_code=400)

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self._workos_connect_token_url(),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                data={
                    "client_id": self._settings.workos_connect_client_id,
                    "client_secret": self._settings.workos_connect_client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self._settings.workos_connect_redirect_uri_effective,
                },
            )

        if response.status_code >= 400:
            raise AuthPlatformError(
                f"WorkOS Standalone Connect token exchange failed with {response.status_code}: {response.text}",
                status_code=502,
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise AuthPlatformError(
                "WorkOS Standalone Connect token response was not valid JSON.",
                status_code=502,
            ) from exc
        if not isinstance(body, dict):
            raise AuthPlatformError(
                "WorkOS Standalone Connect token response must be a JSON object.",
                status_code=502,
            )

        access_token = body.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            raise AuthPlatformError("WorkOS Standalone Connect token response did not include access_token.", status_code=502)
        access_token = access_token.strip()

        auth_payload = get_auth_session_store().get_for_request(request)
        if not isinstance(auth_payload, dict) or "user" not in auth_payload:
            raise AuthPlatformError(
                "The Integration Demo session is missing after the WorkOS Standalone Connect callback.",
                status_code=401,
            )

        refresh_token = body.get("refresh_token")
        if refresh_token is not None and not isinstance(refresh_token, str):
            raise AuthPlatformError(
                "WorkOS Standalone Connect token response returned an invalid refresh_token.",
                status_code=502,
            )

        _clear_marcopolo_auth_state(auth_payload)
        get_auth_session_store().upsert_for_request(request, auth_payload)
        bootstrap = await self._bootstrap_marcopolo(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        auth_payload["marcopolo_access_token"] = access_token
        auth_payload["marcopolo_refresh_token"] = refresh_token
        auth_payload["marcopolo_id_token"] = body.get("id_token")
        auth_payload["marcopolo_token_type"] = body.get("token_type")
        auth_payload["marcopolo_expires_at"] = _compute_expires_at(body.get("expires_in"))
        auth_payload["marcopolo_auth_mode"] = "workos_connect"
        auth_payload["marcopolo_provisioned"] = True
        auth_payload["company"] = bootstrap.company
        auth_payload["namespace"] = bootstrap.namespace
        get_auth_session_store().upsert_for_request(request, auth_payload)

        redirect_to = request.session.pop(
            _WORKOS_CONNECT_RETURN_TO_SESSION_KEY,
            self._default_return_url(with_auth_success=True),
        )
        return RedirectResponse(url=redirect_to, status_code=302)

    async def _bootstrap_marcopolo(
        self,
        *,
        access_token: str,
        refresh_token: str | None,
    ) -> MarcoPoloBootstrap:
        payload: dict[str, str] = {"access_token": access_token}
        if refresh_token:
            payload["refresh_token"] = refresh_token

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self._settings.marcopolo_web_base_url.rstrip('/')}/api/auth/bootstrap",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as exc:
            detail = str(exc).strip() or exc.__class__.__name__
            raise AuthPlatformError(
                f"MarcoPolo bootstrap request failed: {detail}",
                status_code=502,
            ) from exc

        return _parse_marcopolo_bootstrap_response(response)

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

    def _build_workos_connect_authorize_url(self, state: str) -> str:
        query = urlencode(
            {
                "client_id": self._settings.workos_connect_client_id,
                "redirect_uri": self._settings.workos_connect_redirect_uri_effective,
                "response_type": "code",
                "scope": self._settings.workos_connect_scopes,
                "state": state,
            }
        )
        return f"{self._workos_connect_auth_domain()}{self._settings.workos_connect_authorize_path}?{query}"

    def _workos_connect_token_url(self) -> str:
        return f"{self._workos_connect_auth_domain()}{self._settings.workos_connect_token_path}"

    def _workos_connect_complete_url(self) -> str:
        return urljoin(
            self._settings.workos_api_base_url.rstrip("/") + "/",
            self._settings.workos_connect_complete_path.lstrip("/"),
        )

    def _workos_connect_auth_domain(self) -> str:
        return self._settings.workos_connect_auth_url_effective.rstrip("/")



def _split_name(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    parts = [part for part in value.strip().split() if part]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def _normalized_auth_payload_for_mode(auth_payload: dict[str, Any], mode: str) -> dict[str, Any]:
    normalized = dict(auth_payload)
    normalized["marcopolo_auth_mode"] = mode
    if mode != "workos_connect":
        _clear_marcopolo_auth_state(normalized)
    elif not (
        normalized.get("marcopolo_provisioned") is True
        and isinstance(normalized.get("marcopolo_access_token"), str)
        and normalized["marcopolo_access_token"].strip()
        and isinstance(normalized.get("company"), str)
        and normalized["company"].strip()
        and isinstance(normalized.get("namespace"), str)
        and normalized["namespace"].strip()
    ):
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


def _parse_marcopolo_bootstrap_response(response: httpx.Response) -> MarcoPoloBootstrap:
    try:
        payload = response.json()
    except ValueError as exc:
        raise AuthPlatformError(
            f"MarcoPolo bootstrap returned invalid JSON ({response.status_code}).",
            status_code=502,
        ) from exc

    if response.status_code >= 400:
        detail = _bootstrap_response_detail(payload, response)
        raise AuthPlatformError(
            f"MarcoPolo bootstrap failed with {response.status_code}: {detail}",
            status_code=502,
        )

    if not isinstance(payload, dict) or payload.get("success") is not True:
        detail = _bootstrap_response_detail(payload, response)
        raise AuthPlatformError(
            f"MarcoPolo bootstrap response was unsuccessful: {detail}",
            status_code=502,
        )

    data = payload.get("data")
    if not isinstance(data, dict):
        raise AuthPlatformError(
            "MarcoPolo bootstrap response did not include a data object.",
            status_code=502,
        )

    values = {field: data.get(field) for field in ("redirect_url", "company", "namespace")}
    missing_fields = [
        field for field, value in values.items() if not isinstance(value, str) or not value.strip()
    ]
    if missing_fields:
        raise AuthPlatformError(
            "MarcoPolo bootstrap response is missing required data: "
            + ", ".join(missing_fields),
            status_code=502,
        )

    return MarcoPoloBootstrap(
        redirect_url=values["redirect_url"].strip(),
        company=values["company"].strip(),
        namespace=values["namespace"].strip(),
    )


def _bootstrap_response_detail(payload: Any, response: httpx.Response) -> str:
    if isinstance(payload, dict):
        for key in ("error", "detail", "message"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:300]
    text = response.text.strip()
    return text[:300] or "empty response"


def _compute_expires_at(expires_in: Any) -> float | None:
    ttl = _coerce_float(expires_in)
    if ttl is None or ttl <= 0:
        return None
    return time.time() + ttl


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None
