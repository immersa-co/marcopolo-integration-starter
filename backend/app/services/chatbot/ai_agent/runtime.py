from __future__ import annotations

import json
from typing import Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from ....core.config import Settings
from ..service import ChatRun
from ...platform import SkillRegistry
from .context_loader import AgentBootstrapContext, preload_core_skill_context
from .mcp_client import MarcoPoloMcpClient
from .response_parser import extract_preview_rows, extract_tool_error, normalize_tool_payload, parse_tool_message_payload
from .tool_registry import MarcoPoloToolRegistry


class AgentState(TypedDict, total=False):
    messages: list[BaseMessage]
    remaining_steps: int
    final_text: str
    result_kind: str
    table: list[dict[str, Any]]


class TokenUsage(TypedDict, total=False):
    input: int
    output: int
    total: int
    source: str
    approximate: bool
    sharedAcrossToolCalls: int


class IntegrationDemoAgentService:
    def __init__(self, settings: Settings, _marcopolo: Any, skills: SkillRegistry):
        self._settings = settings
        self._skills = skills
        self._bootstrap_context = preload_core_skill_context(skills)
        self._mcp_client = MarcoPoloMcpClient(settings)
        self._tool_registry = MarcoPoloToolRegistry(self._mcp_client)

    async def stream_chat(self, chat_run: ChatRun):
        yield {"event": "status", "data": json.dumps({"message": "Starting MCP-only LangGraph agent"})}

        tools = await self._tool_registry.build_langchain_tools(chat_run.user_session)
        yield {
            "event": "status",
            "data": json.dumps(
                {
                    "message": "Loaded raw MarcoPolo MCP tools",
                    "toolNames": [tool.name for tool in tools],
                }
            ),
        }

        prompt = _system_prompt(self._bootstrap_context)
        yield {
            "event": "debug_context",
            "data": json.dumps(
                {
                    "id": "context-bootstrap",
                    "phase": "bootstrap",
                    "title": "Initial agent context",
                    "systemPrompt": prompt,
                    "bootstrapSkillNames": list(self._bootstrap_context.skill_names),
                    "userMessage": chat_run.message,
                    "toolNames": [tool.name for tool in tools],
                    "messages": [{"type": "human", "content": chat_run.message}],
                }
            ),
        }
        agent = create_react_agent(
            self._model(),
            tools,
            prompt=prompt,
            name="marcopolo_mcp_chat_agent",
        )

        yield {"event": "status", "data": json.dumps({"message": "Running agent loop"})}
        messages: list[BaseMessage] = []
        async for update in agent.astream(
            {"messages": [HumanMessage(content=chat_run.message)]},
            stream_mode="updates",
        ):
            for node_name, payload in update.items():
                if not isinstance(payload, dict):
                    continue
                new_messages = payload.get("messages")
                if isinstance(new_messages, list):
                    messages.extend([message for message in new_messages if isinstance(message, BaseMessage)])
                status = _status_from_update(node_name, payload)
                if status:
                    yield {"event": "status", "data": json.dumps(status)}
                for debug_event in _debug_events_from_update(node_name, payload, prompt=prompt, all_messages=messages):
                    yield {"event": debug_event["event"], "data": json.dumps(debug_event["data"])}

        final_text = _final_ai_text(messages)
        table = _extract_preview_rows(messages)
        result_kind = "table" if table else "text"

        yield {
            "event": "final",
            "data": json.dumps(
                {
                    "message": final_text,
                    "resultKind": result_kind,
                    "table": table,
                }
            ),
        }

    def _model(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self._settings.llm_model,
            api_key=self._settings.llm_api_key,
            base_url=self._settings.llm_api_base_url,
            temperature=0,
        )


def _system_prompt(context: AgentBootstrapContext) -> str:
    sections = [
        "Use the available MarcoPolo MCP tools to answer the user's request.",
        "Rely on tool results rather than unsupported assumptions.",
        "The core MarcoPolo skills below are preloaded and should guide tool use and query authoring.",
        "Connection-specific guidance may be read dynamically from connection workspace files through workspace_shell when relevant.",
    ]

    if context.combined_text:
        sections.extend(
            [
                "",
                "Preloaded MarcoPolo skills:",
                context.combined_text,
            ]
        )

    return "\n".join(sections).strip()


def _final_ai_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = _message_text(message.content)
            if text:
                return text
    return "The agent completed without returning a final natural-language answer."


def _extract_preview_rows(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    for message in reversed(messages):
        if not isinstance(message, ToolMessage):
            continue
        payload = parse_tool_message_payload(message)
        rows = extract_preview_rows(payload, tool_name=message.name)
        if rows:
            return rows[:10]
    return []


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(part for part in parts if part).strip()
    return str(content).strip()


def _status_from_update(node_name: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        return None

    if node_name == "agent":
        for message in messages:
            if isinstance(message, AIMessage) and message.tool_calls:
                tool_names = [str(tool_call.get("name")) for tool_call in message.tool_calls if tool_call.get("name")]
                if tool_names:
                    tool_calls = [
                        {"id": str(tool_call.get("id")), "name": str(tool_call.get("name"))}
                        for tool_call in message.tool_calls
                        if tool_call.get("id") and tool_call.get("name")
                    ]
                    return {
                        "node": node_name,
                        "message": f"Model selected tool call(s): {', '.join(tool_names)}",
                        "toolName": tool_names[0] if len(tool_names) == 1 else None,
                        "toolCallIds": [str(tool_call.get("id")) for tool_call in message.tool_calls if tool_call.get("id")],
                        "toolCalls": tool_calls,
                        "tokenUsage": _extract_token_usage(message, shared_across=len(tool_calls) or len(tool_names)),
                    }
            if isinstance(message, AIMessage):
                text = _message_text(message.content)
                if text:
                    return {
                        "node": node_name,
                        "message": "Model produced final answer",
                    }

    if node_name == "tools":
        for message in messages:
            if isinstance(message, ToolMessage):
                tool_name = message.name or "tool"
                return {
                    "node": node_name,
                    "message": f"Tool returned: {tool_name}",
                    "toolName": tool_name,
                    "toolCallIds": [message.tool_call_id] if message.tool_call_id else [],
                }

    return {
        "node": node_name,
        "message": f"Completed step: {node_name}",
    }


def _debug_events_from_update(
    node_name: str,
    payload: dict[str, Any],
    *,
    prompt: str,
    all_messages: list[BaseMessage],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        return events

    events.append(
        {
            "event": "debug_context",
            "data": {
                "id": f"context-{node_name}-{len(all_messages)}",
                "phase": node_name,
                "title": f"Context after {node_name}",
                "systemPrompt": prompt,
                "messageCount": len(all_messages),
                "messages": [_serialize_message(message) for message in all_messages[-8:]],
            },
        }
    )

    for message in messages:
        if node_name == "agent" and isinstance(message, AIMessage):
            for tool_call in message.tool_calls:
                events.append(
                    {
                        "event": "debug_tool",
                        "data": {
                            "id": str(tool_call.get("id") or f"tool-request-{tool_call.get('name') or 'unknown'}"),
                            "phase": "request",
                            "node": node_name,
                            "toolName": tool_call.get("name"),
                            "toolCallId": tool_call.get("id"),
                            "arguments": tool_call.get("args"),
                            "tokenUsage": _extract_token_usage(message, shared_across=len(message.tool_calls)),
                            "contextSnapshot": {
                                "id": f"context-tool-request-{tool_call.get('id') or tool_call.get('name') or 'unknown'}",
                                "phase": node_name,
                                "title": f"Context for tool request: {tool_call.get('name') or 'unknown'}",
                                "systemPrompt": prompt,
                                "messageCount": len(all_messages),
                                "messages": [_serialize_message(message) for message in all_messages[-8:]],
                            },
                        },
                    }
                )
        if node_name == "tools" and isinstance(message, ToolMessage):
            raw_payload = parse_tool_message_payload(message)
            normalized_payload = normalize_tool_payload(raw_payload, tool_name=message.name)
            events.append(
                {
                    "event": "debug_tool",
                    "data": {
                        "id": f"tool-response-{message.tool_call_id}",
                        "phase": "response",
                        "node": node_name,
                        "toolName": message.name,
                        "toolCallId": message.tool_call_id,
                        "rawPayload": raw_payload,
                        "normalizedPayload": normalized_payload,
                        "previewRows": extract_preview_rows(raw_payload, tool_name=message.name)[:10],
                        "error": extract_tool_error(raw_payload, tool_name=message.name),
                        "contextSnapshot": {
                            "id": f"context-tool-response-{message.tool_call_id or message.name or 'unknown'}",
                            "phase": node_name,
                            "title": f"Context for tool response: {message.name or 'tool'}",
                            "systemPrompt": prompt,
                            "messageCount": len(all_messages),
                            "messages": [_serialize_message(message) for message in all_messages[-8:]],
                        },
                    },
                }
            )

    return events


def _serialize_message(message: BaseMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": message.type,
        "content": _message_text(message.content),
    }
    if isinstance(message, AIMessage):
        payload["toolCalls"] = message.tool_calls
    if isinstance(message, ToolMessage):
        payload["name"] = message.name
        payload["toolCallId"] = message.tool_call_id
    return payload


def _extract_token_usage(message: AIMessage, *, shared_across: int = 1) -> TokenUsage | None:
    usage_metadata = getattr(message, "usage_metadata", None)
    if isinstance(usage_metadata, dict):
        input_tokens = _as_int(usage_metadata.get("input_tokens"))
        output_tokens = _as_int(usage_metadata.get("output_tokens"))
        total_tokens = _as_int(usage_metadata.get("total_tokens"))
        usage = _build_token_usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            source="usage_metadata",
            shared_across=shared_across,
        )
        if usage:
            return usage

    response_metadata = getattr(message, "response_metadata", None)
    if isinstance(response_metadata, dict):
        token_usage = response_metadata.get("token_usage")
        if isinstance(token_usage, dict):
            input_tokens = _as_int(token_usage.get("prompt_tokens") or token_usage.get("input_tokens"))
            output_tokens = _as_int(token_usage.get("completion_tokens") or token_usage.get("output_tokens"))
            total_tokens = _as_int(token_usage.get("total_tokens"))
            usage = _build_token_usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                source="response_metadata.token_usage",
                shared_across=shared_across,
            )
            if usage:
                return usage

    return None


def _build_token_usage(
    *,
    input_tokens: int | None,
    output_tokens: int | None,
    total_tokens: int | None,
    source: str,
    shared_across: int,
) -> TokenUsage | None:
    if input_tokens is None and output_tokens is None and total_tokens is None:
        return None

    if total_tokens is None:
        total_tokens = (input_tokens or 0) + (output_tokens or 0)

    usage: TokenUsage = {
        "source": source,
        "approximate": False,
        "sharedAcrossToolCalls": max(1, shared_across),
    }
    if input_tokens is not None:
        usage["input"] = input_tokens
    if output_tokens is not None:
        usage["output"] = output_tokens
    if total_tokens is not None:
        usage["total"] = total_tokens
    return usage


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None
