from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from marcopolo import Marcopolo
from marcopolo.errors import APIError, MarcopoloError

from ....core.config import Settings
from .mcp_client import MarcoPoloMcpClient, MarcoPoloMcpClientError
from .session_manager import (
    MarcoPoloSession,
    MarcoPoloSessionManager,
    MarcoPoloSessionManagerError,
)
from ....models.api import (
    ConnectionListItem,
    ConnectionTestResultResponse,
    OAuthConnectionTypeOption,
    OAuthConnectionTypesResponse,
    OAuthSetupSessionResponse,
    OAuthSetupStartResponse,
    ConnectionListResponse,
    ConnectionSetupStatusResponse,
    DataConnectionOperation,
    DataConnectionOperationResponse,
    DataConnectionOperationsResponse,
    DemoConnectionInstallResponse,
    EmbeddedConnectionSetupResponse,
    WorkspaceShellResponse,
)
from ...auth import UserSession


class MarcoPoloServiceError(RuntimeError):
    def __init__(self, detail: str, status_code: int = 502):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class DataConnectionOperationSpec:
    id: str
    title: str
    description: str
    prompt: str
    connector_type: str
    connection_name_terms: tuple[str, ...]
    connection_type_candidates: tuple[str, ...]
    query_name: str
    context: str
    payload: dict[str, Any] | list[Any] | str
    payload_format: str | None = None


class MarcoPoloService:
    """MarcoPolo access layer for the Integration Demo."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._session_manager = MarcoPoloSessionManager(settings)
        self._mcp_client = MarcoPoloMcpClient(settings)

    def data_connection_operations(self) -> DataConnectionOperationsResponse:
        return DataConnectionOperationsResponse(
            examples=[
                DataConnectionOperation(
                    id=example.id,
                    title=example.title,
                    description=example.description,
                    prompt=example.prompt,
                    connector_type=example.connector_type,
                )
                for example in _DATA_CONNECTION_OPERATION_SPECS
            ]
        )

    async def list_connections(self, user_session: UserSession) -> ConnectionListResponse:
        session = await self._resolve_session(user_session)
        try:
            async with self._sdk_client(session) as client:
                workspace_connections = await client.workspace.connections()
        except MarcopoloError as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo connections list failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        connections = [
            ConnectionListItem(
                name=item.connection.name,
                type=item.connection.connection_type,
                display_name=item.connection.display_name or item.connection.name,
                capabilities=list(item.capabilities),
                workspace_path=item.workspace_path,
            )
            for item in workspace_connections
        ]
        return ConnectionListResponse(
            connections=connections,
            source="marcopolo-sdk",
            authenticated=True,
        )

    async def invoke_data_connection_operation(
        self,
        user_session: UserSession,
        example_id: str,
    ) -> DataConnectionOperationResponse:
        definition = _DATA_CONNECTION_OPERATION_SPEC_INDEX.get(example_id)
        if definition is None:
            raise MarcoPoloServiceError(
                f"Unknown data connection operation: {example_id}",
                status_code=404,
            )

        connection_list = await self.list_connections(user_session)
        selected = _select_operation_connection(connection_list.connections, definition)
        if selected is None:
            raise MarcoPoloServiceError(
                f"No compatible {definition.title} connection is available for this data connection operation.",
                status_code=404,
            )

        session = await self._resolve_session(user_session)
        try:
            async with self._sdk_client(session) as client:
                operation = await client.operations.query(
                    selected.name,
                    provider_operation=(
                        definition.payload if isinstance(definition.payload, dict) else None
                    ),
                    query_text=(
                        definition.payload if isinstance(definition.payload, str) else None
                    ),
                    inline=True,
                    inline_limit=200,
                )
        except MarcopoloError as exc:
            raise MarcoPoloServiceError(
                f"Data connection operation failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        if operation.status == "failed" or operation.result is None:
            failure = operation.failure.message if operation.failure else "The operation failed."
            raise MarcoPoloServiceError(
                f"Data connection operation failed: {failure}",
                status_code=502,
            )

        records = operation.result.records
        rows = [dict(row) for row in records.rows] if records else []
        reference = operation.result.reference
        row_count = reference.row_count if reference else len(rows)

        return DataConnectionOperationResponse(
            example_id=definition.id,
            title=definition.title,
            message=(
                f"{definition.title} SDK example ran against {selected.display_name} "
                f"and returned {row_count} row{'s' if row_count != 1 else ''}."
            ),
            connection_name=selected.name,
            connection_display_name=selected.display_name,
            connection_type=selected.type,
            query_name=definition.query_name,
            query_file=reference.name if reference else operation.id,
            row_count=row_count,
            rows=rows,
        )

    async def install_demo_connection(
        self,
        user_session: UserSession,
        demo_connection: str,
    ) -> DemoConnectionInstallResponse:
        session = await self._resolve_session(user_session)
        normalized_demo_connection = demo_connection.strip()
        if not normalized_demo_connection:
            raise MarcoPoloServiceError("demoConnection is required.", status_code=422)

        _ = session  # the MCP client resolves its own MarcoPolo session
        try:
            tool_result = await self._mcp_client.call_tool(
                user_session,
                name="install_demo_connection",
                arguments={
                    "demo_connection": normalized_demo_connection,
                    "intent_text": (
                        "Install the hosted demo connection requested from the "
                        f"MarcoPolo Integration Demo: {normalized_demo_connection}"
                    ),
                },
                read_timeout_seconds=180,
            )
        except MarcoPoloMcpClientError as exc:
            raise MarcoPoloServiceError(exc.detail, status_code=exc.status_code) from exc

        payload = _parse_tool_payload(_tool_result_dict(tool_result))
        if not payload.get("success"):
            raise MarcoPoloServiceError(
                str(payload.get("message") or payload.get("error") or "Demo connection install failed."),
                status_code=502,
            )

        return DemoConnectionInstallResponse(
            message=str(payload.get("message") or ""),
            connectionName=str(payload.get("connection_name") or ""),
            displayName=str(payload.get("display_name") or ""),
            type=str(payload.get("type") or ""),
            demoConnectionId=payload.get("demo_connection_id"),
        )

    async def start_connection_setup(
        self,
        user_session: UserSession,
        connection_type: str,
        host_return_url: str | None = None,
        host_origin: str | None = None,
        host_session_id: str | None = None,
    ) -> EmbeddedConnectionSetupResponse:
        try:
            call_result = await self._mcp_client.call_tool(
                user_session,
                name="connection_setup",
                arguments={
                    "type": connection_type,
                    "intent_text": (
                        "Starting a new Integration Demo connection setup flow for the "
                        "authenticated user and preserving the widget payload for the "
                        "embedded setup host."
                    ),
                },
                read_timeout_seconds=120,
            )
        except MarcoPoloMcpClientError as exc:
            raise MarcoPoloServiceError(exc.detail, status_code=exc.status_code) from exc

        tool_result = _inject_embedded_host_context(
            _tool_result_dict(call_result),
            host_return_url=host_return_url,
            host_origin=host_origin,
            host_session_id=host_session_id,
        )
        tool_result = _override_embedded_api_base_url(
            tool_result,
            self._settings.public_api_base_url.rstrip("/") + "/api/connections/ext-app-proxy",
        )
        payload = _parse_tool_payload(tool_result)
        widget_meta = _parse_tool_meta(tool_result)
        return EmbeddedConnectionSetupResponse(
            resource_uri="ui://connection-setup/app.html",
            tool_result=tool_result,
            tool_output=payload,
            widget_meta=widget_meta,
            status_url=payload.get("status_url"),
        )

    async def initiate_embedded_connection_oauth(
        self,
        *,
        widget_token: str,
        connection_type: str,
        display_name: str,
        is_sandbox: bool = False,
    ) -> str:
        url = self._build_server_url("/api/oauth/connection/initiate")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {widget_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={
                    "type": connection_type,
                    "display_name": display_name,
                    "is_sandbox": is_sandbox,
                },
            )

        data = response.json() if response.content else {}
        if response.status_code >= 400:
            detail = (
                data.get("detail")
                or data.get("message")
                or data.get("error")
                or response.text
                or f"MarcoPolo OAuth initiate failed with {response.status_code}"
            )
            raise MarcoPoloServiceError(str(detail), status_code=502 if response.status_code >= 500 else response.status_code)

        oauth_url = data.get("oauth_url")
        if not isinstance(oauth_url, str) or not oauth_url:
            raise MarcoPoloServiceError(
                "MarcoPolo OAuth initiate response did not include oauth_url.",
                status_code=502,
            )

        return oauth_url

    async def read_ui_resource_html(
        self,
        user_session: UserSession,
        resource_uri: str,
    ) -> str:
        try:
            result = await self._mcp_client.read_resource(user_session, uri=resource_uri)
        except MarcoPoloMcpClientError as exc:
            raise MarcoPoloServiceError(exc.detail, status_code=exc.status_code) from exc

        for content in result.contents:
            text = getattr(content, "text", None)
            if isinstance(text, str) and text:
                return text
        raise MarcoPoloServiceError(
            f"MarcoPolo resource {resource_uri} returned no text content.",
            status_code=502,
        )

    async def workspace_shell(
        self,
        user_session: UserSession,
        command: str,
        context: str,
        timeout: int | None = None,
    ) -> WorkspaceShellResponse:
        arguments: dict[str, Any] = {"command": command, "context": context}
        if timeout is not None:
            arguments["timeout"] = timeout
        try:
            call_result = await self._mcp_client.call_tool(
                user_session,
                name="workspace_shell",
                arguments=arguments,
                read_timeout_seconds=(timeout or 120) + 60,
            )
        except MarcoPoloMcpClientError as exc:
            raise MarcoPoloServiceError(exc.detail, status_code=exc.status_code) from exc

        payload = _parse_tool_payload(_tool_result_dict(call_result))
        return WorkspaceShellResponse(
            success=bool(payload.get("success")),
            exit_code=payload.get("exit_code"),
            stdout=str(payload.get("stdout") or ""),
            stderr=str(payload.get("stderr") or ""),
            execution_time=payload.get("execution_time"),
        )

    async def get_connection_setup_status(
        self,
        user_session: UserSession,
        status_url: str,
    ) -> ConnectionSetupStatusResponse:
        session = await self._resolve_session(user_session)
        url = self._build_server_url(status_url)
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                url,
                headers=self._http_headers(session),
            )
        if response.status_code >= 400:
            raise MarcoPoloServiceError(
                f"MarcoPolo setup status lookup failed with {response.status_code}: {response.text}",
                status_code=response.status_code,
            )
        body = response.json()
        return ConnectionSetupStatusResponse(
            setup_session_id=body.get("setup_session_id"),
            status=body.get("status", "unknown"),
            close_popup=body.get("close_popup"),
            resume_embedded=body.get("resume_embedded"),
            refresh_connections=body.get("refresh_connections"),
            connection_name=body.get("connection_name"),
            connection_type=body.get("connection_type"),
            display_name=body.get("display_name"),
            error_code=body.get("error_code"),
            error_message=body.get("error_message"),
            resume_context=body.get("resume_context") or {},
            host_mode=body.get("host_mode"),
            host_return_url=body.get("host_return_url"),
            host_origin=body.get("host_origin"),
            host_session_id=body.get("host_session_id"),
        )

    async def get_embedded_setup_session_status(
        self,
        user_session: UserSession,
        setup_session_id: str,
    ) -> ConnectionSetupStatusResponse:
        session = await self._resolve_session(user_session)
        url = self._build_server_url(f"/api/oauth/connection/setup-sessions/{setup_session_id}/status")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                url,
                headers=self._http_headers(session),
            )
        if response.status_code >= 400:
            raise MarcoPoloServiceError(
                f"MarcoPolo setup session status lookup failed with {response.status_code}: {response.text}",
                status_code=response.status_code,
            )

        body = _unwrap_success_data(response.json())
        return ConnectionSetupStatusResponse(
            setup_session_id=body.get("setup_session_id"),
            status=body.get("status", "unknown"),
            close_popup=body.get("close_popup"),
            resume_embedded=body.get("resume_embedded"),
            refresh_connections=body.get("refresh_connections"),
            connection_name=body.get("connection_name"),
            connection_type=body.get("connection_type"),
            display_name=body.get("display_name"),
            error_code=body.get("error_code"),
            error_message=body.get("error_message"),
            resume_context=body.get("resume_context") or {},
            host_mode=body.get("host_mode"),
            host_return_url=body.get("host_return_url"),
            host_origin=body.get("host_origin"),
            host_session_id=body.get("host_session_id"),
        )

    async def resume_embedded_setup_session(
        self,
        user_session: UserSession,
        setup_session_id: str,
    ) -> EmbeddedConnectionSetupResponse:
        session = await self._resolve_session(user_session)
        url = self._build_server_url(f"/api/oauth/connection/setup-sessions/{setup_session_id}/resume")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                url,
                headers=self._http_headers(session),
            )
        if response.status_code >= 400:
            raise MarcoPoloServiceError(
                f"MarcoPolo setup session resume failed with {response.status_code}: {response.text}",
                status_code=response.status_code,
            )

        body = _unwrap_success_data(response.json())
        tool_output = body.get("tool_output")
        tool_meta = body.get("tool_meta")
        if not isinstance(tool_output, dict) or not isinstance(tool_meta, dict):
            raise MarcoPoloServiceError(
                "MarcoPolo setup session resume did not include embedded tool payload.",
                status_code=502,
            )

        tool_result = {
            "structuredContent": copy.deepcopy(tool_output),
            "_meta": {
                "marcopolo/widget": {
                    **tool_meta,
                    "api_base_url": self._settings.public_api_base_url.rstrip("/") + "/api/connections/ext-app-proxy",
                }
            },
        }
        return EmbeddedConnectionSetupResponse(
            resource_uri="ui://connection-setup/app.html",
            tool_result=tool_result,
            tool_output=tool_output,
            widget_meta=tool_result["_meta"],
            status_url=None,
        )

    async def list_oauth_connection_types(
        self, user_session: UserSession
    ) -> OAuthConnectionTypesResponse:
        session = await self._resolve_session(user_session)
        try:
            async with self._sdk_client(session) as client:
                connection_types = await client.connection_types.list(auth_method="oauth")
        except MarcopoloError as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo connection-type list failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        options = [
            OAuthConnectionTypeOption(
                type=item.connection_type,
                displayName=item.display_name,
                category=item.category,
            )
            for item in connection_types
            # google_drive diverts to folder selection after token exchange,
            # which cannot round-trip through a hosted setup session.
            if not item.deprecated and item.connection_type != "google_drive"
        ]
        options.sort(key=lambda option: option.display_name.lower())
        return OAuthConnectionTypesResponse(connectionTypes=options)

    async def start_oauth_setup(
        self,
        user_session: UserSession,
        *,
        connection_type: str,
        display_name: str,
        client_session_id: str | None = None,
    ) -> OAuthSetupStartResponse:
        session = await self._resolve_session(user_session)
        return_url = f"{self._settings.frontend_base_url.rstrip('/')}/oauth-return"
        try:
            async with self._sdk_client(session) as client:
                started = await client.connection_setup.start(
                    connection_type=connection_type,
                    display_name=display_name,
                    return_url=return_url,
                    client_session_id=client_session_id,
                )
        except (MarcopoloError, ValueError) as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo connection setup start failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        return OAuthSetupStartResponse(
            setupSessionId=started.setup_session_id,
            status=started.status,
            connectionType=started.connection_type,
            connectionName=started.connection_name,
            displayName=started.display_name,
            authorizationUrl=started.authorization_url,
            returnUrl=started.return_url,
            expiresAt=started.expires_at.isoformat(),
        )

    async def get_oauth_setup(
        self,
        user_session: UserSession,
        setup_session_id: str,
    ) -> OAuthSetupSessionResponse:
        session = await self._resolve_session(user_session)
        try:
            async with self._sdk_client(session) as client:
                setup = await client.connection_setup.get(setup_session_id)
        except (MarcopoloError, ValueError) as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo connection setup lookup failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        return OAuthSetupSessionResponse(
            setupSessionId=setup.setup_session_id,
            status=setup.status,
            connectionType=setup.connection_type,
            connectionName=setup.connection_name,
            displayName=setup.display_name,
            expiresAt=setup.expires_at.isoformat(),
            failureCode=setup.failure.code if setup.failure else None,
            failureMessage=setup.failure.message if setup.failure else None,
        )

    async def test_connection(
        self,
        user_session: UserSession,
        connection_name: str,
    ) -> ConnectionTestResultResponse:
        session = await self._resolve_session(user_session)
        try:
            async with self._sdk_client(session) as client:
                outcome = await client.connections.test(connection_name)
        except (MarcopoloError, ValueError) as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo connection test failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        return ConnectionTestResultResponse(
            connectionName=outcome.connection_name,
            status=outcome.status,
            message=outcome.message,
            latencyMs=outcome.latency_ms,
        )

    async def _resolve_session(self, user_session: UserSession) -> MarcoPoloSession:
        try:
            return await self._session_manager.resolve_session(user_session)
        except MarcoPoloSessionManagerError as exc:
            raise MarcoPoloServiceError(exc.detail, status_code=exc.status_code) from exc

    @staticmethod
    def _http_headers(session: MarcoPoloSession) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {session.access_token}",
            "Accept": "application/json",
        }

    def _build_server_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path

        parsed = urlparse(self._settings.marcopolo_mcp_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        return urljoin(origin, path)

    def _sdk_client(self, session: MarcoPoloSession) -> Marcopolo:
        return Marcopolo(
            access_token=session.access_token,
            base_url=self._settings.marcopolo_web_base_url,
        )


def _tool_result_dict(result: Any) -> dict[str, Any]:
    """Normalize an mcp CallToolResult into the dict shape the helpers expect."""
    dumped = result.model_dump(mode="json", by_alias=True)
    if "meta" in dumped and "_meta" not in dumped:
        dumped["_meta"] = dumped.pop("meta")
    return dumped


def _parse_tool_payload(result: dict[str, Any]) -> dict[str, Any]:
    structured = result.get("structuredContent") or result.get("structured_content")
    if isinstance(structured, dict):
        return structured

    result_payload = result.get("result")
    if isinstance(result_payload, dict):
        return result_payload

    for block in result.get("content", []):
        if isinstance(block, dict):
            if isinstance(block.get("structuredContent"), dict):
                return block["structuredContent"]
            if isinstance(block.get("json"), dict):
                return block["json"]
            text = block.get("text")
            if isinstance(text, str):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed

    return {}


def _parse_tool_meta(result: dict[str, Any]) -> dict[str, Any]:
    meta = result.get("_meta")
    if not isinstance(meta, dict):
        meta = result.get("meta")
    if isinstance(meta, dict):
        return meta
    return {}


def _override_embedded_api_base_url(result: dict[str, Any], api_base_url: str) -> dict[str, Any]:
    updated = copy.deepcopy(result)
    meta = updated.get("_meta")
    if not isinstance(meta, dict):
        meta = updated.get("meta")
    if not isinstance(meta, dict):
        return updated

    widget_meta = meta.get("marcopolo/widget")
    if not isinstance(widget_meta, dict):
        return updated

    widget_meta["api_base_url"] = api_base_url
    return updated


def _unwrap_success_data(body: dict[str, Any]) -> dict[str, Any]:
    if isinstance(body.get("data"), dict):
        return body["data"]
    return body


def _inject_embedded_host_context(
    result: dict[str, Any],
    *,
    host_return_url: str | None,
    host_origin: str | None,
    host_session_id: str | None,
) -> dict[str, Any]:
    updated = copy.deepcopy(result)

    def update_payload(payload: dict[str, Any]) -> None:
        payload["host_mode"] = "embedded"
        payload["host_return_url"] = host_return_url
        payload["host_origin"] = host_origin
        payload["host_session_id"] = host_session_id

    structured = updated.get("structuredContent")
    if isinstance(structured, dict):
        update_payload(structured)

    structured_legacy = updated.get("structured_content")
    if isinstance(structured_legacy, dict):
        update_payload(structured_legacy)

    contents = updated.get("content")
    if isinstance(contents, list):
        for item in contents:
            if not isinstance(item, dict):
                continue
            block_payload = item.get("structuredContent")
            if isinstance(block_payload, dict):
                update_payload(block_payload)
            json_payload = item.get("json")
            if isinstance(json_payload, dict):
                update_payload(json_payload)

    return updated


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


def _status_code_from_exception(exc: BaseException) -> int:
    if isinstance(exc, BaseExceptionGroup):
        for item in exc.exceptions:
            status_code = _status_code_from_exception(item)
            if status_code != 502:
                return status_code
        return 502
    if isinstance(exc, MarcoPoloServiceError):
        return exc.status_code
    if isinstance(exc, MarcopoloError):
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return status_code
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    cause = getattr(exc, "__cause__", None)
    if isinstance(cause, BaseException):
        return _status_code_from_exception(cause)
    context = getattr(exc, "__context__", None)
    if isinstance(context, BaseException):
        return _status_code_from_exception(context)
    return 502


_DATA_CONNECTION_OPERATION_SPECS: tuple[DataConnectionOperationSpec, ...] = (
    DataConnectionOperationSpec(
        id="jira_open_tickets",
        title="Jira",
        description="Invoke the SDK against the live Jira JQL connection to load current open tickets for the signed-in Jira user.",
        prompt="List my current open Jira tickets.",
        connector_type="jira",
        connection_name_terms=("jira",),
        connection_type_candidates=("jqljson", "jira"),
        query_name="open_tickets_current_user",
        context="Load current open Jira tickets for the current Jira user.",
        payload={
            "operation": "search_issues",
            "jql": "assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC",
            "fields": ["summary", "assignee", "status", "priority", "project", "created", "updated"],
            "max_results": 25,
        },
    ),
    DataConnectionOperationSpec(
        id="salesforce_top_accounts",
        title="Salesforce",
        description="Invoke the SDK against the live Salesforce connection to list the top five customer accounts by annual revenue.",
        prompt="List top 5 customer accounts by revenue from Salesforce.",
        connector_type="salesforce",
        connection_name_terms=("salesforce",),
        connection_type_candidates=("salesforce",),
        query_name="top_5_accounts_by_revenue",
        context="List the top five Salesforce accounts by annual revenue for the integrations showcase.",
        payload={
            "soql": (
                "SELECT Id, Name, AnnualRevenue, Industry "
                "FROM Account WHERE AnnualRevenue != NULL "
                "ORDER BY AnnualRevenue DESC LIMIT 5"
            ),
        },
    ),
    DataConnectionOperationSpec(
        id="loki_errors_last_24h",
        title="Grafana-Loki",
        description="Invoke the SDK against the live Grafana Loki connection to query recent error logs over the last 24 hours.",
        prompt="Show recent error logs from Loki for the last 24 hours.",
        connector_type="grafana_loki",
        connection_name_terms=("grafana-loki", "grafana loki", "loki"),
        connection_type_candidates=("grafana_loki",),
        query_name="errors_last_24h",
        context="Read recent error logs from Loki.",
        payload={
            "operation": "query_range",
            "query": '{job=~".+"} |~ "(?i)error"',
            "start": "now-24h",
            "end": "now",
            "limit": 200,
            "direction": "backward",
        },
    ),
)

_DATA_CONNECTION_OPERATION_SPEC_INDEX = {
    example.id: example for example in _DATA_CONNECTION_OPERATION_SPECS
}


def _select_operation_connection(
    connections: list[ConnectionListItem],
    definition: DataConnectionOperationSpec,
) -> ConnectionListItem | None:
    for item in connections:
        searchable = f"{item.display_name} {item.name}".lower()
        if any(term in searchable for term in definition.connection_name_terms):
            return item

    for item in connections:
        if item.type in definition.connection_type_candidates:
            return item

    prompt_tokens = {
        token
        for token in definition.prompt.lower().replace("-", " ").split()
        if len(token) > 3
    }
    for item in connections:
        searchable = f"{item.display_name} {item.name} {item.type}".lower()
        if any(token in searchable for token in prompt_tokens):
            return item
    return None
