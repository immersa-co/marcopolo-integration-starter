from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..core.dependencies import (
    get_marcopolo_service,
    require_marcopolo_access,
)
from ..models.api import (
    ConnectionTypeDetailResponse,
    ConnectionTypeListResponse,
    ConnectionListResponse,
    ConnectionTestResultResponse,
    CreateConnectionRequest,
    CreateConnectionResponse,
    DeleteConnectionResponse,
    DemoConnectionInstallResponse,
    ManagedConnectionResponse,
    OAuthConnectionTypesResponse,
    OAuthSetupStartRequest,
    OAuthSetupSessionResponse,
    OAuthSetupStartResponse,
    ReauthorizeConnectionRequest,
    UpdateConnectionRequest,
)
from ..services.auth import UserSession
from ..services.platform import MarcoPoloService, MarcoPoloServiceError

router = APIRouter(prefix="/api/connections", tags=["connections"])


@router.get("", response_model=ConnectionListResponse)
async def list_connections(
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> ConnectionListResponse:
    try:
        return await marcopolo.list_connections(user_session)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/types", response_model=ConnectionTypeListResponse)
async def list_connection_types(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    auth_method: str | None = Query(default=None, alias="authMethod"),
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> ConnectionTypeListResponse:
    try:
        return await marcopolo.list_connection_types(
            user_session,
            search=search,
            category=category,
            auth_method=auth_method,
        )
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/types/{connection_type}", response_model=ConnectionTypeDetailResponse)
async def get_connection_type(
    connection_type: str,
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> ConnectionTypeDetailResponse:
    try:
        return await marcopolo.get_connection_type(user_session, connection_type)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("", response_model=CreateConnectionResponse)
async def create_connection(
    body: CreateConnectionRequest,
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> CreateConnectionResponse:
    try:
        return await marcopolo.create_connection(
            user_session,
            connection_type=body.connection_type,
            display_name=body.display_name,
            setup_method=body.setup_method,
            fields=body.fields,
            share_with_company=body.share_with_company,
        )
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/oauth-types", response_model=OAuthConnectionTypesResponse)
async def list_oauth_connection_types(
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> OAuthConnectionTypesResponse:
    try:
        return await marcopolo.list_oauth_connection_types(user_session)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/oauth-setup", response_model=OAuthSetupStartResponse)
async def start_oauth_setup(
    body: OAuthSetupStartRequest,
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> OAuthSetupStartResponse:
    try:
        return await marcopolo.start_oauth_setup(
            user_session,
            connection_type=body.connection_type,
            display_name=body.display_name,
            client_session_id=body.client_session_id,
        )
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/{connection_name}/reauthorize", response_model=OAuthSetupStartResponse)
async def reauthorize_connection(
    connection_name: str,
    body: ReauthorizeConnectionRequest | None = None,
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> OAuthSetupStartResponse:
    try:
        return await marcopolo.reauthorize_connection(
            user_session,
            connection_name=connection_name,
            client_session_id=body.client_session_id if body is not None else None,
        )
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/oauth-setup/{setup_session_id}", response_model=OAuthSetupSessionResponse)
async def get_oauth_setup(
    setup_session_id: str,
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> OAuthSetupSessionResponse:
    try:
        return await marcopolo.get_oauth_setup(user_session, setup_session_id)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/{connection_name}/test", response_model=ConnectionTestResultResponse)
async def test_connection(
    connection_name: str,
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> ConnectionTestResultResponse:
    try:
        return await marcopolo.test_connection(user_session, connection_name)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/{connection_name}", response_model=ManagedConnectionResponse)
async def get_connection(
    connection_name: str,
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> ManagedConnectionResponse:
    try:
        return await marcopolo.get_connection(user_session, connection_name)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.patch("/{connection_name}", response_model=ManagedConnectionResponse)
async def update_connection(
    connection_name: str,
    body: UpdateConnectionRequest,
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> ManagedConnectionResponse:
    try:
        updated = await marcopolo.update_connection(
            user_session,
            connection_name,
            display_name=body.display_name,
            configuration_patch=body.configuration_patch,
            share_with_company=body.share_with_company,
        )
        current = await marcopolo.get_connection(user_session, updated.name)
        return current
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.delete("/{connection_name}", response_model=DeleteConnectionResponse)
async def delete_connection(
    connection_name: str,
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> DeleteConnectionResponse:
    try:
        return await marcopolo.delete_connection(user_session, connection_name)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/demo-install", response_model=DemoConnectionInstallResponse)
async def install_demo_connection(
    request: Request,
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> DemoConnectionInstallResponse:
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="JSON object body is required.")

    demo_connection = payload.get("demoConnection") or payload.get("demo_connection")
    if not demo_connection:
        raise HTTPException(status_code=422, detail="demoConnection is required.")

    try:
        return await marcopolo.install_demo_connection(user_session, demo_connection)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
