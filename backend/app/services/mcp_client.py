from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import httpx
from mcp import ClientSession, McpError
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client


class MCPClientError(RuntimeError):
    def __init__(self, detail: str, status_code: int = 502):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class BearerTokenAuth(httpx.Auth):
    """Attach a bearer token to outgoing MCP HTTP requests."""

    def __init__(self, token: str) -> None:
        self._token = token

    def auth_flow(self, request: httpx.Request) -> Any:
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request


@dataclass(slots=True)
class MCPClient:
    """Thin wrapper around the official Python MCP SDK."""

    api_token: str
    server_url: str
    timeout_seconds: float = 120.0
    sse_read_timeout_seconds: float = 300.0
    extra_headers: Mapping[str, str] = field(default_factory=dict)
    session_factory: Callable[..., ClientSession] = ClientSession
    http_client_factory: Callable[..., httpx.AsyncClient] = create_mcp_http_client
    streamable_http_factory: Callable[..., Any] = streamable_http_client

    @asynccontextmanager
    async def session(self) -> AsyncIterator[ClientSession]:
        headers = dict(self.extra_headers) or None
        auth = BearerTokenAuth(self.api_token)
        timeout = httpx.Timeout(
            self.timeout_seconds,
            connect=20.0,
            read=self.sse_read_timeout_seconds,
        )
        async with self.http_client_factory(
            headers=headers,
            timeout=timeout,
            auth=auth,
        ) as http_client:
            async with self.streamable_http_factory(
                self.server_url,
                http_client=http_client,
            ) as (read_stream, write_stream, _get_session_id):
                async with self.session_factory(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            async with self.session() as session:
                result = await session.call_tool(name, arguments)
        except McpError as exc:
            raise MCPClientError(
                _format_mcp_error(exc),
                status_code=_status_code_from_mcp_error(exc),
            ) from exc
        except httpx.TimeoutException as exc:
            raise MCPClientError(
                "MarcoPolo MCP request timed out while waiting for the server response.",
                status_code=504,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise MCPClientError(
                f"MarcoPolo MCP request failed: HTTP {exc.response.status_code} {exc.response.text}".strip(),
                status_code=exc.response.status_code,
            ) from exc
        except httpx.HTTPError as exc:
            raise MCPClientError(
                f"MarcoPolo MCP request failed: {exc}",
                status_code=502,
            ) from exc
        return _normalize_result(result.model_dump(mode="json", exclude_none=True))

    async def read_resource(self, uri: str) -> dict[str, Any]:
        try:
            async with self.session() as session:
                result = await session.read_resource(uri)
        except McpError as exc:
            raise MCPClientError(
                _format_mcp_error(exc),
                status_code=_status_code_from_mcp_error(exc),
            ) from exc
        except httpx.TimeoutException as exc:
            raise MCPClientError(
                "MarcoPolo MCP resource read timed out while waiting for the server response.",
                status_code=504,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise MCPClientError(
                f"MarcoPolo MCP resource read failed: HTTP {exc.response.status_code} {exc.response.text}".strip(),
                status_code=exc.response.status_code,
            ) from exc
        except httpx.HTTPError as exc:
            raise MCPClientError(
                f"MarcoPolo MCP resource read failed: {exc}",
                status_code=502,
            ) from exc
        return _normalize_result(result.model_dump(mode="json", exclude_none=True))


def _normalize_result(payload: dict[str, Any]) -> dict[str, Any]:
    if "meta" in payload and "_meta" not in payload:
        payload["_meta"] = payload.pop("meta")
    return payload


def _format_mcp_error(exc: McpError) -> str:
    error = exc.error
    payload = error.model_dump(mode="json", by_alias=True, exclude_none=True)
    return f"MCP error: {payload}"


def _status_code_from_mcp_error(exc: McpError) -> int:
    data = exc.error.data
    if isinstance(data, dict):
        for key in ("status_code", "statusCode"):
            value = data.get(key)
            if isinstance(value, int):
                return value

    code = exc.error.code
    if isinstance(code, int) and code in (401, 403, 404, 409, 422, 429):
        return code
    return 502
