from __future__ import annotations

import re
from typing import Any


def match_visible_connection(message: str, connections: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized_message = _normalize_text(message)
    message_tokens = set(_tokenize(message))
    best_score = 0
    best_connection: dict[str, Any] | None = None

    for connection in connections:
        score = _score_connection_match(connection, normalized_message, message_tokens)
        if score > best_score:
            best_score = score
            best_connection = connection

    if best_score > 0:
        return best_connection

    if len(connections) == 1:
        return connections[0]

    return None


def _score_connection_match(
    connection: dict[str, Any],
    normalized_message: str,
    message_tokens: set[str],
) -> int:
    score = 0
    fields = [
        connection.get("displayName"),
        connection.get("name"),
        connection.get("type"),
        connection.get("workspacePath"),
    ]

    for raw_value in fields:
        if not isinstance(raw_value, str) or not raw_value.strip():
            continue
        normalized_value = _normalize_text(raw_value)
        if len(normalized_value) >= 4 and normalized_value in normalized_message:
            score += 80
        field_tokens = set(_tokenize(raw_value))
        score += len(field_tokens & message_tokens) * 12

    capabilities = {
        str(capability).lower().strip()
        for capability in connection.get("capabilities", [])
        if str(capability).strip()
    }
    browse_terms = {"browse", "folder", "folders", "file", "files", "document", "documents", "directory"}
    query_terms = {
        "query",
        "queries",
        "count",
        "table",
        "rows",
        "issue",
        "issues",
        "ticket",
        "tickets",
        "account",
        "accounts",
        "revenue",
        "error",
        "errors",
        "log",
        "logs",
    }
    if "browse" in capabilities and browse_terms & message_tokens:
        score += 8
    if "query" in capabilities and query_terms & message_tokens:
        score += 8

    return score


def _normalize_text(value: str) -> str:
    return " ".join(_tokenize(value))


def _tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())
