from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from ..config import Settings, get_settings
from ..dependencies import (
    get_auth_service,
    get_current_session,
    require_authenticated_session,
)
from ..marcopolo_auth_modes import get_auth_mode_definition, is_auth_mode_configured
from ..models import AuthSessionResponse
from ..services.auth import AuthPlatformError, AuthPlatformService, UserSession

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/session", response_model=AuthSessionResponse)
async def auth_session(
    request: Request,
    user_session: UserSession = Depends(get_current_session),
    auth_service: AuthPlatformService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> AuthSessionResponse:
    selected_mode = auth_service.selected_marcopolo_auth_mode(request)
    return _build_auth_session_response(
        authenticated=user_session.authenticated,
        configured=auth_service.is_configured,
        provider=user_session.provider,
        user=user_session.user,
        marco_polo_auth_mode=selected_mode,
        marco_polo_configured=is_auth_mode_configured(settings, selected_mode),
        marco_polo_provisioned=user_session.marcopolo_provisioned,
        company=user_session.company,
        namespace=user_session.namespace,
    )


@router.post("/impersonate", response_model=AuthSessionResponse)
async def impersonate_user(
    request: Request,
    email: str = Body(..., embed=True),
    auth_service: AuthPlatformService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> AuthSessionResponse:
    try:
        auth_service.impersonate_user(request, email)
    except AuthPlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    refreshed_session = get_current_session(request)
    selected_mode = auth_service.selected_marcopolo_auth_mode(request)
    return _build_auth_session_response(
        authenticated=refreshed_session.authenticated,
        configured=auth_service.is_configured,
        provider=refreshed_session.provider,
        user=refreshed_session.user,
        marco_polo_auth_mode=selected_mode,
        marco_polo_configured=is_auth_mode_configured(settings, selected_mode),
        marco_polo_provisioned=refreshed_session.marcopolo_provisioned,
        company=refreshed_session.company,
        namespace=refreshed_session.namespace,
    )


@router.post("/marcopolo/mode", response_model=AuthSessionResponse)
async def select_marcopolo_auth_mode(
    request: Request,
    user_session: UserSession = Depends(get_current_session),
    auth_service: AuthPlatformService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> AuthSessionResponse:
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="JSON object body is required.")

    mode = payload.get("mode") or payload.get("authMode")
    if not isinstance(mode, str) or not mode:
        raise HTTPException(status_code=422, detail="mode is required.")

    try:
        selected_mode = auth_service.set_selected_marcopolo_auth_mode(request, mode)
    except AuthPlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    refreshed_session = get_current_session(request)
    return _build_auth_session_response(
        authenticated=refreshed_session.authenticated,
        configured=auth_service.is_configured,
        provider=refreshed_session.provider,
        user=refreshed_session.user,
        marco_polo_auth_mode=selected_mode,
        marco_polo_configured=is_auth_mode_configured(settings, selected_mode),
        marco_polo_provisioned=refreshed_session.marcopolo_provisioned,
        company=refreshed_session.company,
        namespace=refreshed_session.namespace,
    )


@router.get("/marcopolo/authorize")
async def authorize_marcopolo_connect(
    request: Request,
    return_to: str | None = Query(default=None, alias="returnTo"),
    user_session: UserSession = Depends(require_authenticated_session),
    auth_service: AuthPlatformService = Depends(get_auth_service),
) -> RedirectResponse:
    try:
        return await auth_service.authorize_marcopolo_connect(
            request,
            user_session,
            return_to=return_to,
        )
    except AuthPlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/workos/login")
async def workos_connect_login(
    request: Request,
    external_auth_id: str | None = Query(default=None, alias="external_auth_id"),
    user_session: UserSession = Depends(get_current_session),
    auth_service: AuthPlatformService = Depends(get_auth_service),
) -> RedirectResponse:
    try:
        return await auth_service.handle_workos_connect_login(
            request,
            user_session,
            external_auth_id=external_auth_id,
        )
    except AuthPlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/workos/callback")
async def workos_connect_callback(
    request: Request,
    auth_service: AuthPlatformService = Depends(get_auth_service),
) -> RedirectResponse:
    try:
        return await auth_service.complete_workos_connect(request)
    except AuthPlatformError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/logout", response_model=AuthSessionResponse)
async def logout(
    request: Request,
    auth_service: AuthPlatformService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> AuthSessionResponse:
    selected_mode = auth_service.selected_marcopolo_auth_mode(request)
    auth_service.clear_session(request)
    return _build_auth_session_response(
        authenticated=False,
        configured=auth_service.is_configured,
        provider=None,
        user=None,
        marco_polo_auth_mode=selected_mode,
        marco_polo_configured=is_auth_mode_configured(settings, selected_mode),
        marco_polo_provisioned=False,
        company=None,
        namespace=None,
    )


def _build_auth_session_response(
    *,
    authenticated: bool,
    configured: bool,
    provider: str | None,
    user,
    marco_polo_auth_mode: str,
    marco_polo_configured: bool,
    marco_polo_provisioned: bool,
    company: str | None,
    namespace: str | None,
) -> AuthSessionResponse:
    auth_mode_definition = get_auth_mode_definition(marco_polo_auth_mode)
    return AuthSessionResponse(
        authenticated=authenticated,
        configured=configured,
        provider=provider,
        user=user,
        marco_polo_auth_mode=marco_polo_auth_mode,
        marco_polo_auth_mode_label=(
            auth_mode_definition.label if auth_mode_definition else marco_polo_auth_mode
        ),
        marco_polo_auth_mode_configured=marco_polo_configured,
        marco_polo_configured=marco_polo_configured,
        marco_polo_provisioned=marco_polo_provisioned,
        company=company,
        namespace=namespace,
    )
