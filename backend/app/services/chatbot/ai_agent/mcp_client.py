from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import httpx
import mcp.types as mcp_types
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from ....core.config import Settings
from ...auth import UserSession
from ...platform import (
    MarcoPoloSession,
    MarcoPoloSessionManager,
    MarcoPoloSessionManagerError,
)


class MarcoPoloMcpClientError(RuntimeError):
    def __init__(self, detail: str, status_code: int = 502):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class MarcoPoloMcpTool:
    name: str
    description: str | None
    input_schema: dict[str, Any] | None
    output_schema: dict[str, Any] | None
    annotations: dict[str, Any] | None = None


class MarcoPoloMcpClient:
    """Direct MCP client for the Chatbot path.

    This client intentionally avoids marcopolo-sdk so the agent revamp can bind
    directly to raw MarcoPolo MCP tools via the standard MCP client library.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._session_manager = MarcoPoloSessionManager(settings)

    @asynccontextmanager
    async def session(self, user_session: UserSession):
        resolved = await self._resolve_session(user_session)
        http_client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {resolved.access_token}",
            },
            # The first production call can be slow while MarcoPolo initializes
            # the user's workspace context. Keep connect/write generous here so
            # the MCP handshake doesn't fail prematurely.
            timeout=httpx.Timeout(
                connect=120.0,
                read=300.0,
                write=120.0,
                pool=120.0,
            ),
        )
        try:
            async with http_client:
                async with streamable_http_client(
                    self._settings.marcopolo_mcp_url,
                    http_client=http_client,
                ) as (read_stream, write_stream, _get_session_id):
                    client_session = ClientSession(
                        read_stream,
                        write_stream,
                        read_timeout_seconds=timedelta(seconds=300),
                    )
                    async with client_session:
                        await client_session.initialize()
                        yield client_session
        except httpx.HTTPError as exc:
            raise MarcoPoloMcpClientError(
                f"MarcoPolo MCP HTTP transport failed: {_describe_exception(exc)}",
                status_code=502,
            ) from exc
        except Exception as exc:
            raise MarcoPoloMcpClientError(
                f"MarcoPolo MCP session failed: {_describe_exception(exc)}",
                status_code=502,
            ) from exc

    async def list_tools(self, user_session: UserSession) -> list[MarcoPoloMcpTool]:
        async with self.session(user_session) as session:
            result = await session.list_tools()
        return [
            MarcoPoloMcpTool(
                name=tool.name,
                description=tool.description,
                input_schema=tool.inputSchema,
                output_schema=tool.outputSchema,
                annotations=tool.annotations.model_dump(mode="json") if tool.annotations else None,
            )
            for tool in result.tools
        ]

    async def call_tool(
        self,
        user_session: UserSession,
        *,
        name: str,
        arguments: dict[str, Any] | None = None,
        read_timeout_seconds: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> mcp_types.CallToolResult:
        async with self.session(user_session) as session:
            return await session.call_tool(
                name=name,
                arguments=arguments,
                read_timeout_seconds=(
                    timedelta(seconds=read_timeout_seconds) if read_timeout_seconds is not None else None
                ),
                meta=meta,
            )

    async def read_resource(
        self,
        user_session: UserSession,
        *,
        uri: str,
    ) -> mcp_types.ReadResourceResult:
        async with self.session(user_session) as session:
            return await session.read_resource(uri)

    async def list_resources(self, user_session: UserSession) -> mcp_types.ListResourcesResult:
        async with self.session(user_session) as session:
            return await session.list_resources()

    async def _resolve_session(self, user_session: UserSession) -> MarcoPoloSession:
        try:
            return await self._session_manager.resolve_session(user_session)
        except MarcoPoloSessionManagerError as exc:
            raise MarcoPoloMcpClientError(exc.detail, status_code=exc.status_code) from exc


def _describe_exception(exc: BaseException) -> str:
    if isinstance(exc, BaseExceptionGroup):
        parts = [_describe_exception(item) for item in exc.exceptions]
        parts = [part for part in parts if part]
        if parts:
            return " | ".join(parts)
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        request_url = str(response.request.url) if response.request else ""
        prefix = f"HTTP {response.status_code} {response.reason_phrase}".strip()
        if request_url:
            return f"{prefix} for url '{request_url}'"
        return prefix
    detail = str(exc).strip()
    return detail or exc.__class__.__name__
