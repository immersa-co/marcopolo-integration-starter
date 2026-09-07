from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import TypeAdapter
from marcopolo import Marcopolo, ShareScope
from marcopolo._generated.models import ConnectionSetupCreateRequest, ConnectionSetupStart, ReturnUrl
from marcopolo.errors import APIError, MarcopoloError

from ....core.config import Settings
from .mcp_client import MarcoPoloMcpClient, MarcoPoloMcpClientError
from .session_manager import (
    MarcoPoloSession,
    MarcoPoloSessionManager,
    MarcoPoloSessionManagerError,
)
from ....models.api import (
    ConnectionSetupField,
    ConnectionSetupFieldChoice,
    ConnectionSetupFileSpec,
    ConnectionSetupMethod,
    ConnectionListItem,
    DeleteConnectionResponse,
    ConnectionTestResultResponse,
    ConnectionTypeDetailResponse,
    ConnectionTypeListResponse,
    ConnectionTypeSummary,
    ConnectionTypeUiFeatures,
    OAuthConnectionTypeOption,
    OAuthConnectionTypesResponse,
    OAuthSetupSessionResponse,
    OAuthSetupStartResponse,
    ConnectionListResponse,
    ManagedConnectionResponse,
    ManagedConnectionSummary,
    DataConnectionOperation,
    DataConnectionOperationResponse,
    DataConnectionOperationsResponse,
    DemoConnectionInstallResponse,
    CreateConnectionResponse,
    CreatedConnectionSummary,
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
            _normalize_workspace_connection(item)
            for item in workspace_connections
        ]
        return ConnectionListResponse(
            connections=connections,
            source="marcopolo-sdk",
            authenticated=True,
        )

    async def list_connection_types(
        self,
        user_session: UserSession,
        *,
        search: str | None = None,
        category: str | None = None,
        auth_method: str | None = None,
    ) -> ConnectionTypeListResponse:
        session = await self._resolve_session(user_session)
        try:
            async with self._sdk_client(session) as client:
                connection_types = await client.connection_types.list(
                    search=search,
                    category=category,
                    auth_method=auth_method,  # type: ignore[arg-type]
                )
        except (MarcopoloError, ValueError) as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo connection-type list failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        return ConnectionTypeListResponse(
            connectionTypes=[_normalize_connection_type_summary(item) for item in connection_types]
        )

    async def get_connection_type(
        self,
        user_session: UserSession,
        connection_type: str,
    ) -> ConnectionTypeDetailResponse:
        session = await self._resolve_session(user_session)
        try:
            async with self._sdk_client(session) as client:
                details = await client.connection_types.get(connection_type)
        except (MarcopoloError, ValueError) as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo connection-type lookup failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        return _normalize_connection_type_detail(details)

    async def create_connection(
        self,
        user_session: UserSession,
        *,
        connection_type: str,
        display_name: str,
        setup_method: str,
        fields: dict[str, Any],
        share_with_company: bool = False,
    ) -> CreateConnectionResponse:
        session = await self._resolve_session(user_session)
        try:
            async with self._sdk_client(session) as client:
                connection = await client.connections.create(
                    connection_type=connection_type,
                    display_name=display_name,
                    setup_method=setup_method,
                    fields=fields,
                )
                if share_with_company:
                    await client.connections.share(connection.name, ShareScope.COMPANY)
                    connection = await client.connections.get(connection.name)
        except (MarcopoloError, ValueError) as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo connection creation failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        return CreateConnectionResponse(
            connection=CreatedConnectionSummary(
                name=connection.name,
                type=connection.connection_type,
                displayName=connection.display_name,
                category=connection.category,
                authMethod=connection.auth_method,
                canManage=connection.can_manage,
                shareMode=getattr(connection, "share_mode", None),
                sharedWithCompany=getattr(connection, "share_mode", None) == "company",
            ),
            message="Connection created successfully.",
        )

    async def get_connection(
        self,
        user_session: UserSession,
        connection_name: str,
    ) -> ManagedConnectionResponse:
        session = await self._resolve_session(user_session)
        try:
            async with self._sdk_client(session) as client:
                connection = await client.connections.get(connection_name)
                configuration = await client.connections.get_configuration(connection_name)
                connection_type_detail = await client.connection_types.get(connection.connection_type)
        except (MarcopoloError, ValueError) as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo connection lookup failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        normalized_detail = _normalize_connection_type_detail(connection_type_detail)
        return ManagedConnectionResponse(
            connection=_normalize_connection_summary(connection),
            configuration=dict(configuration.configuration),
            connectionTypeDetail=normalized_detail,
            suggestedSetupMethod=_select_suggested_setup_method(
                normalized_detail.setup_methods,
                connection.auth_method,
            ),
            supportsReauthorize=(connection.auth_method == "oauth"),
        )

    async def update_connection(
        self,
        user_session: UserSession,
        connection_name: str,
        *,
        display_name: str | None = None,
        configuration_patch: dict[str, Any] | None = None,
        share_with_company: bool | None = None,
    ) -> ManagedConnectionSummary:
        if display_name is None and not configuration_patch and share_with_company is None:
            raise MarcoPoloServiceError("At least one connection field must be updated", status_code=422)

        session = await self._resolve_session(user_session)
        try:
            async with self._sdk_client(session) as client:
                if display_name is not None or configuration_patch:
                    connection = await client.connections.update(
                        connection_name,
                        display_name=display_name,
                        configuration_patch=configuration_patch,
                    )
                else:
                    connection = await client.connections.get(connection_name)

                if share_with_company is not None:
                    shared_with_company = getattr(connection, "share_mode", None) == "company"
                    if share_with_company and not shared_with_company:
                        await client.connections.share(connection.name, ShareScope.COMPANY)
                        connection = await client.connections.get(connection.name)
                    elif not share_with_company and shared_with_company:
                        await client.connections.unshare(connection.name, ShareScope.COMPANY)
                        connection = await client.connections.get(connection.name)
        except (MarcopoloError, ValueError) as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo connection update failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        return _normalize_connection_summary(connection)

    async def delete_connection(
        self,
        user_session: UserSession,
        connection_name: str,
    ) -> DeleteConnectionResponse:
        session = await self._resolve_session(user_session)
        try:
            async with self._sdk_client(session) as client:
                await client.connections.delete(connection_name)
        except (MarcopoloError, ValueError) as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo connection delete failed: {_describe_exception(exc)}",
                status_code=_status_code_from_exception(exc),
            ) from exc

        return DeleteConnectionResponse(message=f"Deleted connection {connection_name}.")

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
            if not item.deprecated
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
        return_url = _oauth_return_url(self._settings, connection_type)
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

    async def reauthorize_connection(
        self,
        user_session: UserSession,
        *,
        connection_name: str,
        client_session_id: str | None = None,
    ) -> OAuthSetupStartResponse:
        session = await self._resolve_session(user_session)
        try:
            async with self._sdk_client(session) as client:
                connection = await client.connections.get(connection_name)
                if connection.auth_method != "oauth":
                    raise MarcoPoloServiceError(
                        "Only OAuth connections can be re-authorized.",
                        status_code=422,
                    )
                return_url = _oauth_return_url(self._settings, connection.connection_type)

                # The generated request model supports reconnecting an existing
                # OAuth connection, but the high-level SDK helper does not yet
                # expose that parameter on connection_setup.start(...).
                request = ConnectionSetupCreateRequest(
                    connection_type=connection.connection_type,
                    display_name=connection.display_name,
                    return_url=ReturnUrl(return_url),
                    client_session_id=client_session_id,
                    requested_scopes=None,
                    reconnect_connection_name=connection.name,
                    is_sandbox=None,
                    source_variant=None,
                )
                response = await client.connection_setup._request_json(
                    "POST",
                    "/api/v1/connection-setup-sessions",
                    request.model_dump(mode="json", exclude_none=True),
                )
                started = response.validate(TypeAdapter(ConnectionSetupStart), "connection setup start")
        except MarcoPoloServiceError:
            raise
        except (MarcopoloError, ValueError) as exc:
            raise MarcoPoloServiceError(
                f"MarcoPolo connection re-authorization failed: {_describe_exception(exc)}",
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


def _normalize_connection_type_summary(item: Any) -> ConnectionTypeSummary:
    return ConnectionTypeSummary(
        type=item.connection_type,
        displayName=item.display_name,
        category=item.category,
        description=item.description,
        authMethods=list(item.auth_methods),
        setupMethodKinds=sorted(
            {method.kind for method in (item.setup_methods or []) if getattr(method, "kind", None)}
        ),
        requiresOAuth=item.ui_features.requires_oauth,
        deprecated=bool(item.deprecated),
    )


def _normalize_workspace_connection(item: Any) -> ConnectionListItem:
    return ConnectionListItem(
        name=item.connection.name,
        type=item.connection.connection_type,
        displayName=item.connection.display_name or item.connection.name,
        authMethod=item.connection.auth_method,
        canManage=bool(item.connection.can_manage),
        accessReason=getattr(item.connection, "access_reason", None),
        shareMode=getattr(item.connection, "share_mode", None),
        sharedWithCompany=getattr(item.connection, "share_mode", None) == "company",
        capabilities=list(item.capabilities),
        workspacePath=item.workspace_path,
    )


def _normalize_connection_summary(item: Any) -> ManagedConnectionSummary:
    return ManagedConnectionSummary(
        name=item.name,
        type=item.connection_type,
        displayName=item.display_name,
        authMethod=item.auth_method,
        canManage=bool(item.can_manage),
        accessReason=item.access_reason,
        category=item.category,
        connectionTypeDisplayName=item.connection_type_display_name,
        isDemoConnection=bool(item.is_demo_connection),
        isOwner=bool(item.is_owner),
        isPersonal=bool(item.is_personal),
        owner=item.owner,
        shareMode=item.share_mode,
        sharedWithCompany=item.share_mode == "company",
    )


def _select_suggested_setup_method(
    setup_methods: list[ConnectionSetupMethod],
    auth_method: str,
) -> str | None:
    if auth_method == "oauth":
        oauth_method = next((method for method in setup_methods if method.kind == "hosted_oauth"), None)
        return oauth_method.method if oauth_method else None
    fields_method = next((method for method in setup_methods if method.kind == "fields"), None)
    return fields_method.method if fields_method else (setup_methods[0].method if setup_methods else None)


def _oauth_return_url(settings: Settings, connection_type: str) -> str | None:
    # Google Drive hosted OAuth is accepted by MarcoPolo only as a first-party
    # setup flow today. Sending a third-party return URL causes the setup start
    # request to be rejected even though the connection type advertises
    # hosted_oauth support in metadata.
    if connection_type == "google_drive":
        return None
    return f"{settings.frontend_base_url.rstrip('/')}/oauth-return"


def _normalize_connection_type_detail(item: Any) -> ConnectionTypeDetailResponse:
    return ConnectionTypeDetailResponse(
        type=item.connection_type,
        displayName=item.display_name,
        category=item.category,
        description=item.description,
        authMethods=list(item.auth_methods),
        uiFeatures=ConnectionTypeUiFeatures(
            deleteWarning=item.ui_features.delete_warning,
            filePicker=list(item.ui_features.file_picker),
            isFileProvider=item.ui_features.is_file_provider,
            isPersonal=item.ui_features.is_personal,
            logoKey=item.ui_features.logo_key,
            requiresOAuth=item.ui_features.requires_oauth,
            supportsDownload=item.ui_features.supports_download,
            supportsUpload=item.ui_features.supports_upload,
            usesLocalFilePicker=item.ui_features.uses_local_file_picker,
        ),
        setupMethods=[
            ConnectionSetupMethod(
                method=method.method,
                kind=method.kind,
                category=method.category,
                displayName=method.display_name,
                description=method.description,
                fields=[
                    ConnectionSetupField(
                        advanced=field.advanced,
                        choices=(
                            [
                                ConnectionSetupFieldChoice(label=choice.label, value=choice.value)
                                for choice in field.choices
                            ]
                            if field.choices
                            else None
                        ),
                        default=field.default,
                        description=field.description,
                        file=(
                            ConnectionSetupFileSpec(
                                allowCreateEmpty=field.file.allow_create_empty,
                                extensions=list(field.file.extensions) if field.file.extensions else None,
                                infoText=field.file.info_text,
                                maxSizeMb=field.file.max_size_mb,
                            )
                            if field.file
                            else None
                        ),
                        groupLabel=field.group_label,
                        itemType=field.item_type,
                        label=field.label,
                        minItems=field.min_items,
                        name=field.name,
                        required=field.required,
                        secret=bool(field.secret),
                        type=field.type,
                    )
                    for field in method.fields
                ],
            )
            for method in (item.setup_methods or [])
        ],
    )


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
