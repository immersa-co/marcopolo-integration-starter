from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import ToolMessage


def parse_tool_message_payload(message: ToolMessage) -> Any:
    content = message.content
    if isinstance(content, str):
        parsed = _parse_json_like(content)
        return parsed if parsed is not None else {"raw": content}

    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if not isinstance(text, str):
                continue
            parsed = _parse_json_like(text)
            if parsed is not None:
                return parsed
        return {"raw": content}

    return {"raw": content}


def normalize_tool_payload(payload: Any, *, tool_name: str | None = None) -> Any:
    if tool_name == "workspace_shell":
        return _normalize_workspace_shell_payload(payload)
    return payload


def extract_preview_rows(payload: Any, *, tool_name: str | None = None) -> list[dict[str, Any]]:
    normalized = normalize_tool_payload(payload, tool_name=tool_name)
    return _extract_rows_from_payload(normalized)


def extract_tool_error(payload: Any, *, tool_name: str | None = None) -> str | None:
    normalized = normalize_tool_payload(payload, tool_name=tool_name)
    return _extract_error_from_payload(normalized)


def _normalize_workspace_shell_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload

    structured = payload.get("structuredContent")
    if not isinstance(structured, dict):
        structured = payload.get("structured_content")
    if not isinstance(structured, dict):
        return payload

    normalized = dict(structured)
    stdout_parsed = _parse_json_like(normalized.get("stdout"))
    if stdout_parsed is not None:
        normalized["stdout_parsed"] = stdout_parsed
    stderr_parsed = _parse_json_like(normalized.get("stderr"))
    if stderr_parsed is not None:
        normalized["stderr_parsed"] = stderr_parsed
    if isinstance(payload.get("isError"), bool):
        normalized["isError"] = payload["isError"]
    return normalized


def _extract_rows_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in (
            "stdout_parsed",
            "structuredContent",
            "structured_content",
            "connections",
            "rows",
            "items",
            "data",
            "preview",
            "results",
        ):
            rows = _extract_rows_from_payload(payload.get(key))
            if rows:
                return rows
        return []

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, str):
        parsed = _parse_json_like(payload)
        if parsed is None:
            return []
        return _extract_rows_from_payload(parsed)

    return []


def _extract_error_from_payload(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in ("stdout", "stderr"):
            nested = _extract_error_from_payload(payload.get(key))
            if nested:
                return nested

        if payload.get("isError") is True or payload.get("success") is False:
            for key in ("message", "error", "stderr", "stdout"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        exit_code = payload.get("exit_code")
        if isinstance(exit_code, int) and exit_code != 0:
            stderr = payload.get("stderr")
            if isinstance(stderr, str) and stderr.strip():
                return stderr.strip()

        for key in ("stdout_parsed", "stderr_parsed"):
            nested = _extract_error_from_payload(payload.get(key))
            if nested:
                return nested

    if isinstance(payload, str):
        parsed = _parse_json_like(payload)
        if parsed is not None:
            return _extract_error_from_payload(parsed)

    return None


def _parse_json_like(value: Any) -> Any | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None
