from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from marcopolo import MarcoPolo as SDKMarcoPolo
from marcopolo.errors import ToolResultError

from ....core.config import Settings
from .session_manager import (
    MarcoPoloSession,
    MarcoPoloSessionManager,
    MarcoPoloSessionManagerError,
)
from ....models.api import (
    ConnectionListItem,
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
        client = self._sdk_client(session)
        try:
            result = await client.list_connections(
                context="Loading the authenticated user's visible MarcoPolo connections for the Integration Demo connections tab and agent discovery workflow.",
                timeout=60,
            )
        except Exception as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo connections list failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        connections = [
            ConnectionListItem(
                name=item.name,
                type=item.connection_type,
                display_name=item.display_name or item.name,
                capabilities=item.capabilities,
                workspace_path=item.workspace_path,
            )
            for item in result.connections
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
        client = self._sdk_client(session)
        try:
            result = await client.execute(
                selected.name,
                definition.payload,
                query_name=definition.query_name,
                context=definition.context,
                payload_format=definition.payload_format,
                timeout=180,
            )
        except Exception as exc:
            raise MarcoPoloServiceError(
                f"Data connection operation failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        return DataConnectionOperationResponse(
            example_id=definition.id,
            title=definition.title,
            message=(
                f"{definition.title} SDK example ran against {selected.display_name} "
                f"and returned {result.row_count} row{'s' if result.row_count != 1 else ''}."
            ),
            connection_name=selected.name,
            connection_display_name=selected.display_name,
            connection_type=selected.type,
            query_name=definition.query_name,
            query_file=result.query_file,
            row_count=result.row_count,
            rows=result.rows,
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

        client = self._sdk_client(session)
        try:
            result = await client.install_demo_connection(
                normalized_demo_connection,
                intent_text=(
                    "Install the hosted demo connection requested from the "
                    f"MarcoPolo Integration Demo: {normalized_demo_connection}"
                ),
            )
        except ToolResultError as exc:
            raise MarcoPoloServiceError(str(exc), status_code=502) from exc
        except Exception as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo demo connection install failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        return DemoConnectionInstallResponse(
            message=result.message,
            connectionName=result.connection_name,
            displayName=result.display_name,
            type=result.connection_type,
            demoConnectionId=result.demo_connection_id,
        )

    async def start_connection_setup(
        self,
        user_session: UserSession,
        connection_type: str,
        host_return_url: str | None = None,
        host_origin: str | None = None,
        host_session_id: str | None = None,
    ) -> EmbeddedConnectionSetupResponse:
        session = await self._resolve_session(user_session)
        client = self._sdk_client(session)
        try:
            result = await client.start_connection_setup(
                connection_type,
                context="Starting a new Integration Demo connection setup flow for the authenticated user and preserving the widget payload for the embedded setup host.",
            )
        except ToolResultError as exc:
            raise MarcoPoloServiceError(str(exc), status_code=502) from exc
        except Exception as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo connection setup failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        tool_result = _inject_embedded_host_context(
            result.tool_result,
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
            resource_uri=result.resource_uri,
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
        session = await self._resolve_session(user_session)
        client = self._sdk_client(session)
        try:
            result = await client.read_resource_text(resource_uri)
        except ToolResultError as exc:
            raise MarcoPoloServiceError(str(exc), status_code=502) from exc
        except Exception as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo resource read failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        return result.text

    async def workspace_shell(
        self,
        user_session: UserSession,
        command: str,
        context: str,
        timeout: int | None = None,
    ) -> WorkspaceShellResponse:
        session = await self._resolve_session(user_session)
        client = self._sdk_client(session)
        try:
            result = await client.workspace_shell(
                command,
                context=context,
                timeout=timeout,
            )
        except ToolResultError as exc:
            raise MarcoPoloServiceError(str(exc), status_code=502) from exc
        except Exception as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo workspace shell failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        return WorkspaceShellResponse(
            success=result.success,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            execution_time=result.execution_time,
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

    def _sdk_client(self, session: MarcoPoloSession) -> SDKMarcoPolo:
        return SDKMarcoPolo(
            api_token=session.access_token,
            server_url=self._settings.marcopolo_mcp_url,
        )


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
