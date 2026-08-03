from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, Field, create_model

from ...auth import UserSession
from .mcp_client import MarcoPoloMcpClient, MarcoPoloMcpTool


class MarcoPoloToolRegistry:
    """Bind raw MarcoPolo MCP tools into a LangChain-compatible tool surface."""

    def __init__(self, mcp_client: MarcoPoloMcpClient):
        self._mcp_client = mcp_client

    async def list_tools(self, user_session: UserSession) -> list[MarcoPoloMcpTool]:
        return await self._mcp_client.list_tools(user_session)

    async def build_langchain_tools(self, user_session: UserSession) -> list[StructuredTool]:
        tools = await self.list_tools(user_session)
        return [self._bind_tool(user_session, tool) for tool in tools]

    def _bind_tool(self, user_session: UserSession, tool: MarcoPoloMcpTool) -> StructuredTool:
        args_schema = _args_schema_for_tool(tool)

        async def _invoke(**kwargs: Any) -> dict[str, Any]:
            result = await self._mcp_client.call_tool(
                user_session,
                name=tool.name,
                arguments=kwargs or None,
            )
            return result.model_dump(mode="json", by_alias=True)

        description_parts = [tool.description.strip()] if tool.description else []
        if tool.input_schema:
            description_parts.append(f"Input JSON schema: {tool.input_schema}")

        return StructuredTool.from_function(
            coroutine=_invoke,
            name=tool.name,
            description="\n\n".join(description_parts).strip() or tool.name,
            args_schema=args_schema,
            infer_schema=False,
        )


class _ToolArgsBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _args_schema_for_tool(tool: MarcoPoloMcpTool) -> type[BaseModel]:
    schema = tool.input_schema or {}
    properties = schema.get("properties") if isinstance(schema, dict) else None
    required = set(schema.get("required", [])) if isinstance(schema, dict) else set()
    if not isinstance(properties, dict):
        return create_model(f"{_safe_model_name(tool.name)}Args", __base__=_ToolArgsBase)

    fields: dict[str, tuple[Any, Any]] = {}
    for name, prop in properties.items():
        annotation = _annotation_from_json_schema(prop if isinstance(prop, dict) else {})
        default = ... if name in required else _default_from_json_schema(prop if isinstance(prop, dict) else {})
        fields[name] = (
            annotation,
            Field(default=default, description=_description_from_json_schema(prop if isinstance(prop, dict) else {})),
        )

    return create_model(
        f"{_safe_model_name(tool.name)}Args",
        __base__=_ToolArgsBase,
        **fields,
    )


def _annotation_from_json_schema(schema: dict[str, Any]) -> Any:
    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        non_null = [item for item in any_of if isinstance(item, dict) and item.get("type") != "null"]
        if len(non_null) == 1:
            return _annotation_from_json_schema(non_null[0]) | None
        return Any | None

    schema_type = schema.get("type")
    if schema_type == "string":
        return str
    if schema_type == "integer":
        return int
    if schema_type == "number":
        return float
    if schema_type == "boolean":
        return bool
    if schema_type == "object":
        return dict[str, Any]
    if schema_type == "array":
        return list[Any]
    return Any


def _default_from_json_schema(schema: dict[str, Any]) -> Any:
    if "default" in schema:
        return schema["default"]

    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        allows_null = any(isinstance(item, dict) and item.get("type") == "null" for item in any_of)
        if allows_null:
            return None

    return None


def _description_from_json_schema(schema: dict[str, Any]) -> str | None:
    description = schema.get("description")
    return description if isinstance(description, str) and description.strip() else None


def _safe_model_name(name: str) -> str:
    parts = [part for part in name.replace("-", "_").split("_") if part]
    if not parts:
        return "MarcoPoloTool"
    return "".join(part[:1].upper() + part[1:] for part in parts)
