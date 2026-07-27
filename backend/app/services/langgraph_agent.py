from __future__ import annotations

import json
import re
from pathlib import PurePosixPath
from typing import Any, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from ..config import Settings
from ..models import UserProfile
from .chat import ChatRun
from .auth import UserSession
from .marcopolo import MarcoPoloService
from .skills import SkillRegistry


class AgentState(TypedDict, total=False):
    message: str
    user: UserProfile
    user_session: UserSession
    connections: list[dict[str, Any]]
    selected_connection: dict[str, Any] | None
    target_type: str | None
    guidance: str
    plan: dict[str, Any]
    execution: dict[str, Any]
    final_text: str
    result_kind: str
    table: list[dict[str, Any]]
    error: str


class IntegrationDemoAgentService:
    def __init__(self, settings: Settings, marcopolo: MarcoPoloService, skills: SkillRegistry):
        self._settings = settings
        self._marcopolo = marcopolo
        self._skills = skills
        self._graph = self._build_graph()

    async def stream_chat(self, chat_run: ChatRun):
        initial_state: AgentState = {
            "message": chat_run.message,
            "user": chat_run.user_session.user,
        }
        accumulated: AgentState = initial_state.copy()

        yield {"event": "status", "data": json.dumps({"message": "Starting LangGraph agent"})}
        async for update in self._graph.astream(
            {
                **initial_state,
                "user_session": chat_run.user_session,  # type: ignore[typeddict-item]
            },
            stream_mode="updates",
        ):
            for node_name, payload in update.items():
                if payload is None:
                    continue
                accumulated.update(payload)
                yield {
                    "event": "status",
                    "data": json.dumps({"node": node_name, "message": _node_status(node_name, payload)}),
                }

        if accumulated.get("error"):
            yield {"event": "error", "data": json.dumps({"message": accumulated["error"]})}
        else:
            yield {
                "event": "final",
                "data": json.dumps(
                    {
                        "message": accumulated.get("final_text", ""),
                        "resultKind": accumulated.get("result_kind", "text"),
                        "table": accumulated.get("table", []),
                    }
                ),
            }

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("discover_connections", self._discover_connections)
        graph.add_node("select_connection", self._select_connection)
        graph.add_node("load_guidance", self._load_guidance)
        graph.add_node("plan_execution", self._plan_execution)
        graph.add_node("execute_plan", self._execute_plan)
        graph.add_node("format_response", self._format_response)
        graph.add_edge(START, "discover_connections")
        graph.add_edge("discover_connections", "select_connection")
        graph.add_edge("select_connection", "load_guidance")
        graph.add_edge("load_guidance", "plan_execution")
        graph.add_edge("plan_execution", "execute_plan")
        graph.add_edge("execute_plan", "format_response")
        graph.add_edge("format_response", END)
        return graph.compile()

    async def _discover_connections(self, state: AgentState) -> dict[str, Any]:
        user_session = state["user_session"]  # type: ignore[index]
        response = await self._marcopolo.list_connections(user_session)
        return {
            "connections": [item.model_dump(by_alias=True) for item in response.connections],
        }

    async def _select_connection(self, state: AgentState) -> dict[str, Any]:
        connections = state.get("connections", [])
        if not connections:
            return {
                "target_type": None,
                "selected_connection": None,
                "error": "No visible MarcoPolo connections are available yet.",
            }

        selected = _match_visible_connection(state["message"], connections)
        if selected is None:
            selected = await self._llm_select_connection(state["message"], connections)

        if selected is None:
            available_names = [
                str(connection.get("displayName") or connection.get("name") or connection.get("type"))
                for connection in connections[:8]
            ]
            available_suffix = " ..." if len(connections) > 8 else ""
            return {
                "target_type": None,
                "selected_connection": None,
                "error": (
                    "I could not map that request to a visible connection. "
                    "Mention the connection or datasource more explicitly. "
                    f"Available connections: {', '.join(available_names)}{available_suffix}."
                ),
            }

        return {
            "target_type": selected.get("type"),
            "selected_connection": selected,
        }

    async def _llm_select_connection(
        self,
        message: str,
        connections: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not self._settings.llm_api_key:
            return None

        llm = ChatOpenAI(
            model=self._settings.llm_model,
            api_key=self._settings.llm_api_key,
            base_url=self._settings.llm_api_base_url,
            temperature=0,
        )
        prompt = f"""
You are selecting the best MarcoPolo connection for a user request.

User request:
{message}

Visible connections:
{json.dumps([
    {
        "name": connection.get("name"),
        "display_name": connection.get("displayName"),
        "type": connection.get("type"),
        "capabilities": connection.get("capabilities", []),
    }
    for connection in connections
], indent=2)}

Return JSON only using one of these shapes:
1. {{"mode":"select","connection_name":"<exact connection name>"}}
2. {{"mode":"clarify"}}

Select a connection only when one visible connection is clearly the best fit.
Prefer exact product or datasource matches such as Jira, GitHub, Snowflake, Salesforce, Google Drive, or Grafana.
"""
        try:
            response = await llm.ainvoke(prompt)
            selection = json.loads(response.content)
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

        if selection.get("mode") != "select":
            return None

        connection_name = selection.get("connection_name")
        if not isinstance(connection_name, str) or not connection_name:
            return None

        return next(
            (
                connection
                for connection in connections
                if connection.get("name") == connection_name
            ),
            None,
        )

    async def _load_guidance(self, state: AgentState) -> dict[str, Any]:
        if state.get("error") or state.get("selected_connection") is None:
            return {}

        user_session = state["user_session"]  # type: ignore[index]
        name = state["selected_connection"]["name"]
        shell = await self._marcopolo.workspace_shell(
            user_session,
            command=f"cat connections/{name}/README.md connections/{name}/RULES.md connections/{name}/SYNTAX.md",
            context="Reading workspace connection guidance files for the integration demo chat workflow before authoring a user-specific query.",
            timeout=60,
        )
        guidance_parts = [shell.stdout]
        for skill_name in ("query-and-analyze", "using-connection-cli", "using-marcopolo-workspace"):
            skill = self._skills.get(skill_name)
            if skill:
                guidance_parts.append(f"# Skill: {skill.name}\n{skill.body}")
        return {"guidance": "\n\n".join(guidance_parts)}

    async def _plan_execution(self, state: AgentState) -> dict[str, Any]:
        if state.get("error") or state.get("selected_connection") is None:
            return {}

        selected = state["selected_connection"]
        capabilities = selected.get("capabilities", [])
        message = state["message"]

        if "folder" in message.lower() and "browse" in capabilities:
            return {"plan": {"mode": "browse"}}

        if not self._settings.llm_api_key:
            return {
                "error": "LLM API key is missing, so the agent cannot author a connection-specific query yet.",
            }

        llm = ChatOpenAI(
            model=self._settings.llm_model,
            api_key=self._settings.llm_api_key,
            base_url=self._settings.llm_api_base_url,
            temperature=0,
        )
        prompt = f"""
You are planning a MarcoPolo Integration Demo query.

User request:
{message}

Selected connection:
{json.dumps(selected, indent=2)}

Guidance:
{state.get("guidance", "")}

Return JSON only with one of these shapes:
1. {{"mode":"browse"}}
2. {{"mode":"clarify","clarification":"..."}}
3. {{"mode":"query_file","query_file_path":"connections/<name>/queries/<file>","query_contents":"..."}}

Use browse only when the request is best served by `connection browse`.
Use query_file when the request requires a query file followed by `connection query`.
When authoring query_contents for preview-style requests, keep the result set bounded in the query itself, for example with `LIMIT 20` or the connector's equivalent.
Use clarify when the request lacks enough detail.
"""
        response = await llm.ainvoke(prompt)
        plan = json.loads(response.content)
        return {"plan": plan}

    async def _execute_plan(self, state: AgentState) -> dict[str, Any]:
        if state.get("error") or state.get("selected_connection") is None:
            return {}

        plan = state.get("plan", {})
        user_session = state["user_session"]  # type: ignore[index]
        connection_name = state["selected_connection"]["name"]

        if plan.get("mode") == "clarify":
            return {"execution": {"mode": "clarify", "clarification": plan["clarification"]}}

        if plan.get("mode") == "browse":
            shell = await self._marcopolo.workspace_shell(
                user_session,
                command=f"connection browse {connection_name} --json",
                context="Browsing a configured file-provider connection to answer an integration demo user request about accessible folders and documents.",
                timeout=60,
            )
            return {"execution": {"mode": "browse", "shell": shell.model_dump(by_alias=True)}}

        if plan.get("mode") != "query_file":
            return {"error": "Agent planning did not produce a recognized execution mode."}

        query_path = plan["query_file_path"]
        query_contents = plan["query_contents"]
        persist_command = _workspace_write_command(query_path, query_contents)
        persist = await self._marcopolo.workspace_shell(
            user_session,
            command=persist_command,
            context="Writing a durable MarcoPolo query file in the workspace before executing the integration demo user request.",
            timeout=60,
        )
        if not persist.success:
            return {"error": f"Query file authoring failed: {persist.stderr or persist.stdout}"}

        shell = await self._marcopolo.workspace_shell(
            user_session,
            command=f"connection query {connection_name} --file {query_path} --include-results --json",
            context="Executing a MarcoPolo connection query for the integration demo chatbot and collecting inline rows for response formatting.",
            timeout=120,
        )
        return {
            "execution": {
                "mode": "query_file",
                "query_file_path": query_path,
                "shell": shell.model_dump(by_alias=True),
            }
        }

    async def _format_response(self, state: AgentState) -> dict[str, Any]:
        if state.get("error"):
            return {"final_text": state["error"], "result_kind": "text", "table": []}

        execution = state.get("execution", {})
        if execution.get("mode") == "clarify":
            return {"final_text": execution["clarification"], "result_kind": "text", "table": []}

        shell = execution.get("shell", {})
        stdout = shell.get("stdout", "")
        parsed = _parse_shell_stdout(stdout)

        shell_error = _extract_shell_error(shell, parsed)
        if shell_error:
            return {"final_text": shell_error, "result_kind": "text", "table": []}

        if execution.get("mode") == "browse":
            rows = parsed.get("items") if isinstance(parsed.get("items"), list) else parsed if isinstance(parsed, list) else []
            rows = rows[:10] if isinstance(rows, list) else []
            connection_label = _connection_label(state.get("selected_connection"))
            return {
                "final_text": (
                    f"Found {len(rows)} accessible folders and documents in {connection_label}. "
                    "Open any result below to inspect its details."
                ),
                "result_kind": "browse",
                "table": rows,
            }

        preview_rows = []
        if isinstance(parsed, dict):
            preview_rows = _extract_query_rows(parsed)
        connection_label = _connection_label(state.get("selected_connection"))
        return {
            "final_text": f"Executed the MarcoPolo query against {connection_label} and returned the preview rows below.",
            "result_kind": "table",
            "table": preview_rows[:10] if isinstance(preview_rows, list) else [],
        }

def _match_visible_connection(message: str, connections: list[dict[str, Any]]) -> dict[str, Any] | None:
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
        overlap = len(field_tokens & message_tokens)
        score += overlap * 12

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


def _connection_label(connection: dict[str, Any] | None) -> str:
    if not isinstance(connection, dict):
        return "the selected connection"
    label = connection.get("displayName") or connection.get("name") or connection.get("type")
    return str(label) if label else "the selected connection"


def _node_status(node_name: str, payload: dict[str, Any]) -> str:
    if payload.get("error"):
        return payload["error"]
    mapping = {
        "discover_connections": "Loaded visible MarcoPolo connections",
        "select_connection": "Selected the best matching connection",
        "load_guidance": "Read connection guidance and skills",
        "plan_execution": "Prepared execution plan",
        "execute_plan": "Executed workspace action",
        "format_response": "Formatted final response",
    }
    return mapping.get(node_name, node_name)


def _workspace_write_command(path: str, contents: str) -> str:
    posix_path = PurePosixPath(path)
    eof_token = "__MPINTEGRATION_QUERY__"
    return (
        f"mkdir -p {sh_quote(str(posix_path.parent))} && cat > {sh_quote(str(posix_path))} <<'{eof_token}'\n"
        f"{contents}\n"
        f"{eof_token}"
    )


def _parse_shell_stdout(stdout: str) -> dict[str, Any] | list[Any]:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"raw": stdout}


def _extract_query_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("data", "preview", "rows", "items"):
        rows = _extract_rows(payload.get(key))
        if rows:
            return rows
    return []


def _extract_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        candidate_rows = value.get("rows") or value.get("items")
        if isinstance(candidate_rows, list):
            return [row for row in candidate_rows if isinstance(row, dict)]
        return []
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return _extract_rows(parsed)
    return []


def _extract_shell_error(
    shell: dict[str, Any],
    parsed: dict[str, Any] | list[Any],
) -> str | None:
    if shell.get("success") is False:
        if isinstance(parsed, dict):
            for key in ("message", "error", "stderr"):
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        for key in ("stderr", "stdout", "message", "error"):
            value = shell.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    if isinstance(parsed, dict) and parsed.get("success") is False:
        for key in ("message", "error"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"
