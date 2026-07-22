from __future__ import annotations

import httpx
import json
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response

from ..dependencies import (
    get_settings,
    get_marcopolo_service,
    require_marcopolo_access,
)
from ..models import (
    ConnectionListResponse,
    ConnectionSetupResponse,
    ConnectionSetupStatusResponse,
    DemoConnectionInstallResponse,
)
from ..models import (
    EmbeddedConnectionOAuthInitiateResponse,
    EmbeddedConnectionSetupResponse,
    EmbeddedSetupSessionLookupResponse,
)
from ..services.auth import UserSession
from ..services.marcopolo import MarcoPoloService, MarcoPoloServiceError

router = APIRouter(prefix="/api/connections", tags=["connections"])
_HOST_SESSION_LOOKUPS: dict[str, str] = {}


@router.get("", response_model=ConnectionListResponse)
async def list_connections(
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> ConnectionListResponse:
    try:
        return await marcopolo.list_connections(user_session)
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


@router.post("/setup", response_model=ConnectionSetupResponse)
async def start_connection_setup(
    request: Request,
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> ConnectionSetupResponse:
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="JSON object body is required.")

    connection_type = payload.get("connectionType") or payload.get("connection_type")
    if not connection_type:
        raise HTTPException(status_code=422, detail="connectionType is required.")

    try:
        return await marcopolo.start_connection_setup(user_session, connection_type)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/setup/embedded", response_model=EmbeddedConnectionSetupResponse)
async def start_embedded_connection_setup(
    request: Request,
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> EmbeddedConnectionSetupResponse:
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="JSON object body is required.")

    connection_type = payload.get("connectionType") or payload.get("connection_type")
    host_return_url = payload.get("hostReturnUrl") or payload.get("host_return_url")
    host_origin = payload.get("hostOrigin") or payload.get("host_origin")
    host_session_id = payload.get("hostSessionId") or payload.get("host_session_id")
    if not connection_type:
        raise HTTPException(status_code=422, detail="connectionType is required.")

    try:
        return await marcopolo.start_embedded_connection_setup(
            user_session,
            connection_type,
            host_return_url=host_return_url,
            host_origin=host_origin,
            host_session_id=host_session_id,
        )
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/setup/oauth-initiate", response_model=EmbeddedConnectionOAuthInitiateResponse)
async def initiate_embedded_connection_oauth(
    request: Request,
    _user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> EmbeddedConnectionOAuthInitiateResponse:
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="JSON object body is required.")

    connection_type = payload.get("connectionType") or payload.get("connection_type")
    display_name = payload.get("displayName") or payload.get("display_name")
    widget_token = payload.get("widgetToken") or payload.get("widget_token")
    is_sandbox = bool(payload.get("isSandbox") or payload.get("is_sandbox"))

    if not connection_type:
        raise HTTPException(status_code=422, detail="connectionType is required.")
    if not display_name:
        raise HTTPException(status_code=422, detail="displayName is required.")
    if not widget_token:
        raise HTTPException(status_code=422, detail="widgetToken is required.")

    try:
        oauth_url = await marcopolo.initiate_embedded_connection_oauth(
            widget_token=widget_token,
            connection_type=connection_type,
            display_name=display_name,
            is_sandbox=is_sandbox,
        )
        return EmbeddedConnectionOAuthInitiateResponse(oauth_url=oauth_url)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/ext-app/connection-setup")
async def get_connection_setup_ext_app(
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
    resource_uri: str = Query(default="ui://connection-setup/app.html", alias="resourceUri"),
) -> HTMLResponse:
    try:
        html = await marcopolo.read_ui_resource_html(user_session, resource_uri)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    response = HTMLResponse(html, media_type="text/html")
    response.headers["Cache-Control"] = "no-store"
    return response


@router.api_route("/ext-app-proxy/{proxy_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_ext_app_api(
    proxy_path: str,
    request: Request,
    settings=Depends(get_settings),
) -> Response:
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header is required.")

    upstream = urlparse(settings.marcopolo_api_base_url)
    target_origin = f"{upstream.scheme}://{upstream.netloc}"
    target_url = f"{target_origin.rstrip('/')}/{proxy_path.lstrip('/')}"
    body = await request.body()
    headers = {
        "Authorization": auth_header,
        "Accept": request.headers.get("accept", "application/json"),
    }
    content_type = request.headers.get("content-type")
    if content_type:
        headers["Content-Type"] = content_type

    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        upstream = await client.request(
            request.method,
            target_url,
            params=request.query_params.multi_items(),
            headers=headers,
            content=body or None,
        )

    response_content = upstream.content
    if request.method == "POST" and proxy_path.rstrip("/") == "api/oauth/connection/initiate":
        try:
            request_payload = json.loads(body.decode("utf-8")) if body else {}
            response_payload = json.loads(response_content.decode("utf-8")) if response_content else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            request_payload = {}
            response_payload = {}

        host_session_id = request_payload.get("host_session_id")
        setup_session_id = response_payload.get("setup_session_id")
        if isinstance(host_session_id, str) and host_session_id and isinstance(setup_session_id, str) and setup_session_id:
            _HOST_SESSION_LOOKUPS[host_session_id] = setup_session_id

    response_headers: dict[str, str] = {}
    for header_name in ("content-type", "location", "cache-control"):
        header_value = upstream.headers.get(header_name)
        if header_value:
            response_headers[header_name] = header_value

    return Response(
        content=response_content,
        status_code=upstream.status_code,
        headers=response_headers,
    )


@router.get("/setup-status", response_model=ConnectionSetupStatusResponse)
async def get_connection_setup_status(
    status_url: str = Query(alias="statusUrl"),
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> ConnectionSetupStatusResponse:
    try:
        return await marcopolo.get_connection_setup_status(user_session, status_url)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/setup-session-status", response_model=ConnectionSetupStatusResponse)
async def get_embedded_setup_session_status(
    setup_session_id: str = Query(alias="setupSessionId"),
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> ConnectionSetupStatusResponse:
    try:
        return await marcopolo.get_embedded_setup_session_status(user_session, setup_session_id)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/setup-session-resume", response_model=EmbeddedConnectionSetupResponse)
async def resume_embedded_setup_session(
    setup_session_id: str = Query(alias="setupSessionId"),
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> EmbeddedConnectionSetupResponse:
    try:
        return await marcopolo.resume_embedded_setup_session(user_session, setup_session_id)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/setup-session-lookup", response_model=EmbeddedSetupSessionLookupResponse)
async def lookup_embedded_setup_session(
    host_session_id: str = Query(alias="hostSessionId"),
    _user_session: UserSession = Depends(require_marcopolo_access),
) -> EmbeddedSetupSessionLookupResponse:
    setup_session_id = _HOST_SESSION_LOOKUPS.get(host_session_id)
    if not setup_session_id:
        raise HTTPException(status_code=404, detail="Setup session not found for host session.")
    return EmbeddedSetupSessionLookupResponse(setup_session_id=setup_session_id)
