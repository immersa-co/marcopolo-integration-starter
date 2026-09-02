"""Compatibility shim: the MCP client now lives in the platform layer."""

from ...platform.marcopolo.mcp_client import (
    MarcoPoloMcpClient,
    MarcoPoloMcpClientError,
    MarcoPoloMcpTool,
)

__all__ = ["MarcoPoloMcpClient", "MarcoPoloMcpClientError", "MarcoPoloMcpTool"]
